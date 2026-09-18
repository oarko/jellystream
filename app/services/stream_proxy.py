"""ffmpeg-based stream proxy.

Finds the currently playing ScheduleEntry for a channel, calculates the
elapsed offset, and pipes the media through ffmpeg starting at that offset.
This makes the channel behave like real TV — viewers always join mid-show.

When one entry ends the generator automatically transitions to the next
scheduled entry so the stream runs continuously without the client
needing to reconnect.
"""

import asyncio
import json
import os
from asyncio.subprocess import PIPE
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.logging_config import get_logger
from app.integrations.jellyfin import JellyfinClient
from app.models.channel import Channel
from app.models.schedule_entry import ScheduleEntry

logger = get_logger(__name__)

# ffmpeg output format sent to Jellyfin Live TV clients
_OUTPUT_FORMAT = "mpegts"
_MEDIA_TYPE = "video/mp2t"

# How long (seconds) to wait when there is a gap in the schedule before
# re-checking whether a new entry has become available.
_GAP_POLL_INTERVAL = 5

# Valid hwaccel backends — kept in sync with app/api/channels.py VALID_HWACCEL.
_VALID_HWACCEL = {"none", "vaapi", "qsv", "nvenc"}
_DEFAULT_VAAPI_DEVICE = "/dev/dri/renderD128"

# Target video bitrate for hardware encoders, which don't support libx264's
# -crf quality-based mode — kept equal to the software path's -maxrate so
# quality is roughly comparable across backends.
_HWACCEL_BITRATE = "8000k"

# nvenc's named presets (p1=fastest/lowest quality .. p7=slowest/highest
# quality) don't share libx264's naming, unlike h264_qsv which accepts the
# same preset names as libx264 directly.
_NVENC_PRESET_MAP = {
    "ultrafast": "p1",
    "superfast": "p2",
    "veryfast": "p3",
    "faster": "p4",
    "fast": "p5",
    "medium": "p6",
}


def _get_client() -> JellyfinClient:
    return JellyfinClient(
        base_url=settings.JELLYFIN_URL,
        api_key=settings.JELLYFIN_API_KEY,
        user_id=settings.JELLYFIN_USER_ID or None,
        client_name=getattr(settings, "JELLYFIN_CLIENT_NAME", "JellyStream"),
        device_name=getattr(settings, "JELLYFIN_DEVICE_NAME", "JellyStream Server"),
        device_id=getattr(settings, "JELLYFIN_DEVICE_ID", None),
    )


async def get_current_entry(
    channel_id: int, db: AsyncSession
) -> Optional[ScheduleEntry]:
    """
    Return the ScheduleEntry that spans the current UTC time for a channel.

    Returns None if nothing is scheduled right now.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    logger.debug(
        f"get_current_entry: channel_id={channel_id}, now={now.isoformat()}"
    )

    result = await db.execute(
        select(ScheduleEntry)
        .where(
            ScheduleEntry.channel_id == channel_id,
            ScheduleEntry.start_time <= now,
            ScheduleEntry.end_time > now,
        )
        .order_by(ScheduleEntry.start_time)
        .limit(1)
    )
    entry = result.scalar_one_or_none()

    if entry:
        offset = (now - entry.start_time).total_seconds()
        logger.debug(
            f"get_current_entry: found '{entry.title}' "
            f"(id={entry.id}), offset={offset:.1f}s"
        )
    else:
        logger.debug(f"get_current_entry: no entry found for channel {channel_id}")

    return entry


async def get_next_entry(
    channel_id: int, after_entry: ScheduleEntry, db: AsyncSession
) -> Optional[ScheduleEntry]:
    """
    Return the ScheduleEntry that comes immediately after `after_entry` in
    this channel's timeline (ordered by start_time), regardless of the
    current wall-clock time.

    Used by _continuous_stream_generator to advance from one entry to the
    next by playback order rather than by re-deriving position from "now" —
    see that function's docstring for why that distinction matters.
    """
    logger.debug(
        f"get_next_entry: channel_id={channel_id}, after entry id={after_entry.id} "
        f"start_time={after_entry.start_time.isoformat()}"
    )

    result = await db.execute(
        select(ScheduleEntry)
        .where(
            ScheduleEntry.channel_id == channel_id,
            ScheduleEntry.start_time > after_entry.start_time,
        )
        .order_by(ScheduleEntry.start_time)
        .limit(1)
    )
    entry = result.scalar_one_or_none()

    if entry:
        logger.debug(f"get_next_entry: found '{entry.title}' (id={entry.id})")
    else:
        logger.debug(
            f"get_next_entry: no further entries scheduled for channel {channel_id}"
        )

    return entry


async def _detect_preferred_audio_index(source: str) -> Optional[int]:
    """
    Run ffprobe to find the absolute stream index of the first audio track
    matching settings.PREFERRED_AUDIO_LANGUAGE.

    Compares against both 2-letter (en) and 3-letter (eng) ISO 639 codes so
    that files tagged either way are handled correctly.

    Returns the stream index (int) if found, or None to fall back to the
    first audio track.
    """
    want = settings.PREFERRED_AUDIO_LANGUAGE.lower().strip()
    if not want:
        return None

    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-select_streams", "a",
            source,
            stdout=PIPE,
            stderr=PIPE,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            await proc.wait()
            logger.warning(
                f"_detect_preferred_audio_index: ffprobe timed out for {source!r}"
            )
            return None

        data = json.loads(stdout)
        for stream in data.get("streams", []):
            tags = stream.get("tags") or {}
            lang = (
                tags.get("language") or tags.get("LANGUAGE") or ""
            ).lower().strip()
            if lang and (lang == want or lang[:2] == want[:2]):
                idx = stream.get("index")
                logger.debug(
                    f"_detect_preferred_audio_index: "
                    f"preferred language '{want}' found at stream index {idx}"
                )
                return idx

        logger.debug(
            f"_detect_preferred_audio_index: "
            f"no '{want}' audio track found, using default"
        )

    except Exception as exc:
        logger.warning(f"_detect_preferred_audio_index: ffprobe failed: {exc}")

    return None


def _build_ffmpeg_cmd(
    source: str,
    offset_seconds: int,
    audio_stream_index: Optional[int] = None,
    max_height: Optional[int] = 1080,
    preset: str = "veryfast",
    hwaccel: str = "none",
    hwaccel_device: Optional[str] = None,
    hw_decode: bool = True,
) -> list:
    """
    Build the ffmpeg command for one schedule entry.

    max_height: scale down to this height (keeping aspect ratio) if the
        source is taller; None or 0 = pass the native resolution through.
    preset: libx264 speed/quality preset. Also accepted as-is by h264_qsv
        (which uses the same preset names); mapped to nvenc's p1-p7 scale
        for "nvenc"; ignored entirely for "vaapi", which has no equivalent.
    hwaccel: "none" (software libx264, default) | "vaapi" | "qsv" | "nvenc".
        Falls back to "none" if given an unrecognized value.
    hwaccel_device: optional explicit device (e.g. "/dev/dri/renderD128" for
        vaapi) for machines with more than one GPU. Blank = auto-detect.
    hw_decode: when hwaccel is set, whether to also try decoding on the GPU
        (True, default) or always decode in software and only hand frames to
        the GPU for encoding (False). Hardware decode is the harder of the
        two to support — many GPUs' fixed-function decoders don't implement
        older/unusual codecs at all (e.g. legacy MPEG-4 Part 2), and there's
        nothing ffmpeg can do about that; it's a real hardware gap, not a
        flag we can work around. Hardware ENCODE has no such dependency on
        the source codec — it just needs raw decoded frames, which software
        decode always produces regardless of the source format. _play_entry
        uses this to retry with hw_decode=False before giving up on hardware
        entirely, so a hardware-incompatible source codec costs only the
        (usually cheaper) decode-side saving, not all of it.
    """
    # When any -map is present ffmpeg disables automatic stream selection, so
    # we must map both video and audio explicitly.  If ffprobe identified a
    # preferred-language track use its absolute index; otherwise fall back to
    # the first audio stream in the file.
    audio_map = (
        ["-map", f"0:{audio_stream_index}"]
        if audio_stream_index is not None
        else ["-map", "0:a:0"]
    )

    if hwaccel not in _VALID_HWACCEL:
        logger.warning(f"_build_ffmpeg_cmd: unrecognized hwaccel {hwaccel!r}, using software")
        hwaccel = "none"

    scale_needed = bool(max_height and max_height > 0)
    cmd = ["ffmpeg"]

    # ── Hardware device init (must precede -i). Needed whenever hwaccel is
    # set at all, even with hw_decode=False — the encoder still needs a
    # device context to allocate hardware surfaces on.
    if hwaccel == "vaapi":
        cmd += ["-vaapi_device", hwaccel_device or _DEFAULT_VAAPI_DEVICE]
    elif hwaccel == "qsv":
        cmd += ["-init_hw_device", f"qsv=hw:{hwaccel_device or 'auto'}", "-filter_hw_device", "hw"]
    elif hwaccel == "nvenc":
        cmd += ["-init_hw_device", f"cuda=cu:{hwaccel_device or '0'}", "-filter_hw_device", "cu"]

    # ── Input / seek ─────────────────────────────────────────────────────────
    cmd += [
        "-ss", str(offset_seconds),    # fast seek in local file / HTTP Range
        "-probesize", "262144",        # 256 KB probe instead of default 5 MB
        "-analyzeduration", "1000000", # 1 s analysis instead of default 5 s
        "-fflags", "nobuffer",         # pass frames through without extra buffering
    ]

    if hw_decode and hwaccel == "vaapi":
        cmd += ["-hwaccel", "vaapi", "-hwaccel_output_format", "vaapi"]
    elif hw_decode and hwaccel == "qsv":
        cmd += ["-hwaccel", "qsv", "-hwaccel_output_format", "qsv"]
    elif hw_decode and hwaccel == "nvenc":
        cmd += ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]

    cmd += ["-i", source, "-map", "0:v:0", *audio_map]

    # ── Video filter — get frames onto the GPU for encoding (when hwaccel is
    # set) and/or scale, in whichever combination the decode path requires.
    upload_filter = {"vaapi": "hwupload", "qsv": "hwupload", "nvenc": "hwupload_cuda"}.get(hwaccel)
    scale_expr = f"scale=-2:min({max_height}\\,ih)" if scale_needed else None
    vf_parts: list = []

    if hwaccel == "none":
        if scale_expr:
            vf_parts = [scale_expr]
    elif hw_decode:
        # Frames are already GPU-resident from decode. Only round-trip
        # through system memory if a scale is actually needed — this is the
        # most broadly-compatible way to scale (the alternative, scale_vaapi/
        # vpp_qsv, has expression-syntax support that varies by driver) — the
        # frame is small, so this costs little CPU next to the decode/encode
        # work already offloaded to the GPU. If no scaling is needed, skip
        # filtering entirely and stay fully GPU-resident end to end.
        if scale_expr:
            vf_parts = ["hwdownload", "format=nv12", scale_expr, "format=nv12", upload_filter]
    else:
        # Software decode (hw_decode=False): frames start in system memory,
        # so just scale (if needed) then upload once for the encoder.
        if scale_expr:
            vf_parts.append(scale_expr)
        vf_parts += ["format=nv12", upload_filter]

    if vf_parts:
        cmd += ["-vf", ",".join(vf_parts)]

    # ── Video codec ──────────────────────────────────────────────────────────
    if hwaccel == "vaapi":
        cmd += ["-c:v", "h264_vaapi", "-b:v", _HWACCEL_BITRATE]
    elif hwaccel == "qsv":
        cmd += ["-c:v", "h264_qsv", "-preset", preset, "-b:v", _HWACCEL_BITRATE]
    elif hwaccel == "nvenc":
        nvenc_preset = _NVENC_PRESET_MAP.get(preset, "p3")
        cmd += ["-c:v", "h264_nvenc", "-preset", nvenc_preset, "-b:v", _HWACCEL_BITRATE]
    else:
        cmd += [
            "-c:v", "libx264",
            "-preset", preset,          # fast encode, lower CPU than slow/medium
            "-tune", "zerolatency",     # minimize encoder buffering for live use
            "-crf", "20",               # visually lossless at typical bitrates
        ]
    cmd += ["-maxrate", "8000k", "-bufsize", "4000k"]

    # ── Audio — AAC stereo ────────────────────────────────────────────────
    cmd += [
        "-c:a", "aac",
        "-b:a", "192k",
        "-ac", "2",                    # downmix to stereo
        # ── Output ───────────────────────────────────────────────────────────
        "-f", _OUTPUT_FORMAT,          # MPEG-TS container
        "-loglevel", "warning",
        "pipe:1",
    ]
    return cmd


async def _resolve_source(entry: ScheduleEntry, channel_id: int) -> str:
    """Return the local file path or Jellyfin HTTP URL for an entry."""
    if entry.file_path and os.path.isfile(entry.file_path):
        logger.info(
            f"_resolve_source: channel={channel_id}, title='{entry.title}' — local file"
        )
        return entry.file_path

    client = _get_client()
    source = await client.get_stream_url(entry.media_item_id)
    if entry.file_path:
        logger.warning(
            f"_resolve_source: '{entry.file_path}' not accessible, "
            f"falling back to Jellyfin HTTP stream"
        )
    else:
        logger.info(
            f"_resolve_source: channel={channel_id}, title='{entry.title}' — HTTP stream"
        )
    return source


async def _drain_stderr(process, tail: bytearray, max_tail: int = 4000) -> None:
    """
    Continuously read ffmpeg's stderr so the pipe never fills up and blocks
    the process — nothing else reads it — keeping only the last max_tail
    bytes around in case we need to log them on failure.
    """
    try:
        while True:
            chunk = await process.stderr.read(4096)
            if not chunk:
                break
            tail.extend(chunk)
            if len(tail) > max_tail:
                del tail[: len(tail) - max_tail]
    except Exception:
        pass


async def _play_entry(
    entry: ScheduleEntry,
    offset_seconds: int,
    channel: Channel,
    channel_id: int,
    chunk_size: int,
):
    """
    Resolve the entry's source and stream it through ffmpeg using the
    channel's configured transcode settings (max_height / preset / hwaccel),
    yielding MPEG-TS chunks.

    When hwaccel is set, tries up to three tiers in order, each one only
    if the previous produced zero bytes of output:
      1. hardware decode + hardware encode (cheapest, but requires the GPU
         to support the source's codec/profile — many GPUs' fixed-function
         decoders don't implement older/unusual codecs like legacy MPEG-4
         Part 2 at all, which is a real hardware gap, not something any
         ffmpeg flag can work around)
      2. software decode + hardware encode (works for any source codec,
         since the encoder only needs raw decoded frames and doesn't care
         how they were produced — this is what makes hardware encoding
         actually apply "all the time it's selected", regardless of the
         source's codec, at the cost of losing only the decode-side saving
         for that one file)
      3. full software (libx264) — the final safety net if hardware encode
         itself is unavailable (bad driver/device), so nothing is ever
         skipped regardless of what's wrong.
    """
    try:
        source = await _resolve_source(entry, channel_id)
    except Exception as exc:
        logger.error(
            f"_play_entry: could not resolve source for entry {entry.id} "
            f"'{entry.title}': {exc}",
            exc_info=True,
        )
        await asyncio.sleep(2)  # brief backoff in case Jellyfin is unreachable
        return

    audio_idx = await _detect_preferred_audio_index(source)
    hwaccel = channel.hwaccel or "none"

    stages = (
        [("none", True)]
        if hwaccel == "none"
        else [(hwaccel, True), (hwaccel, False), ("none", True)]
    )

    for stage_index, (stage_hwaccel, hw_decode) in enumerate(stages):
        is_last_stage = stage_index == len(stages) - 1

        cmd = _build_ffmpeg_cmd(
            source, offset_seconds, audio_idx,
            max_height=channel.transcode_max_height,
            preset=channel.transcode_preset,
            hwaccel=stage_hwaccel,
            hwaccel_device=channel.hwaccel_device,
            hw_decode=hw_decode,
        )
        logger.debug(
            f"_play_entry: starting ffmpeg for '{entry.title}' (id={entry.id}), "
            f"offset={offset_seconds}s, hwaccel={stage_hwaccel}, hw_decode={hw_decode}, "
            f"audio_stream={audio_idx if audio_idx is not None else 'default'}"
        )

        try:
            process = await asyncio.create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
        except FileNotFoundError:
            logger.error("_play_entry: ffmpeg not found")
            return  # Cannot recover — end the stream

        stderr_tail = bytearray()
        stderr_task = asyncio.create_task(_drain_stderr(process, stderr_tail))
        bytes_yielded = 0
        try:
            while True:
                chunk = await process.stdout.read(chunk_size)
                if not chunk:
                    break
                bytes_yielded += len(chunk)
                yield chunk
        finally:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            await process.wait()
            stderr_task.cancel()
            try:
                await stderr_task
            except (asyncio.CancelledError, Exception):
                pass

        # A clean finish needs BOTH some output AND a zero exit code.
        # bytes_yielded alone isn't enough: a process that gets killed
        # partway through (e.g. the OOM killer, under combined load from
        # several concurrently-transcoding channels) still closes its stdout
        # pipe, which looks identical to a normal EOF if we only check
        # whether any bytes came out — silently truncating playback to
        # whatever had been written so far and racing on to the next
        # scheduled entry as if this one had played in full.
        returncode = process.returncode
        success = bytes_yielded > 0 and returncode == 0

        if success:
            logger.info(
                f"_play_entry: channel={channel_id} '{entry.title}' finished "
                f"(hwaccel={stage_hwaccel}, hw_decode={hw_decode}, bytes_yielded={bytes_yielded})"
            )
            return

        if is_last_stage:
            # No further fallback tier to try. Still move on to the next
            # scheduled entry rather than retrying this one indefinitely —
            # but say clearly that this was NOT a clean finish, so a crash
            # doesn't get silently mistaken for the movie having ended.
            logger.error(
                f"_play_entry: channel={channel_id} '{entry.title}' gave up after "
                f"exhausting all fallback tiers (hwaccel={stage_hwaccel}, "
                f"hw_decode={hw_decode}, returncode={returncode}, "
                f"bytes_yielded={bytes_yielded}) — moving on to the next scheduled "
                f"entry. ffmpeg stderr tail: {bytes(stderr_tail)[-2000:]!r}"
            )
            return

        # Not the last stage: either produced nothing, or exited abnormally
        # despite some partial output — either way, try the next, more
        # conservative tier rather than treating this as a normal finish.
        logger.error(
            f"_play_entry: hwaccel={stage_hwaccel} hw_decode={hw_decode} "
            f"{'produced no output' if bytes_yielded == 0 else f'exited abnormally (returncode={returncode}) after {bytes_yielded} bytes'} "
            f"for '{entry.title}' (channel={channel_id}), trying next fallback "
            f"stage. ffmpeg stderr tail: {bytes(stderr_tail)[-2000:]!r}"
        )


async def _continuous_stream_generator(
    channel_id: int, db: AsyncSession, chunk_size: int = 65536
):
    """
    Yield MPEG-TS chunks indefinitely, transitioning between schedule entries
    as each one ends.

    The channel's transcode settings (hwaccel/preset/max_height) are
    re-fetched from the database fresh before every entry, not captured once
    when the connection opens. A connection here can legitimately run for
    hours across many titles — that's the whole point of this generator —
    so if settings were only read once, changing a channel's hardware
    acceleration setting while someone is already watching it would be
    silently ignored for that viewer's entire remaining session, with
    nothing in the logs to explain why the UI and the actual running stream
    disagree. Re-fetching costs one extra indexed query per title (at most
    a couple of hours apart), which is negligible.

    The *first* entry for a new connection is picked by wall clock (via
    get_current_entry) so a viewer tuning in mid-show joins at the correct
    offset, like real broadcast TV.

    Every entry after that is picked by playback order (via get_next_entry)
    and started at offset 0 — NOT by re-querying wall clock. Schedule entries
    are sized from Jellyfin's reported RunTimeTicks, which can differ
    slightly from a file's real playable duration. If we re-derived offset
    from "now" on every transition, a file that runs even a few seconds
    longer or shorter than its metadata would leave wall clock out of sync
    with actual playback, and the next item would start already partway in
    (or replay the tail of the one that just finished). Following playback
    order instead of the clock means nothing is ever skipped or repeated —
    at the cost of this one connection's timeline drifting from the nominal
    schedule over a long session, which is the far smaller problem.

    If there is a gap in the schedule the generator waits _GAP_POLL_INTERVAL
    seconds between retries instead of killing the connection.
    """
    previous_entry: Optional[ScheduleEntry] = None

    while True:
        offset_seconds = 0

        if previous_entry is None:
            entry = await get_current_entry(channel_id, db)
            if entry:
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                offset_seconds = max(0, int((now - entry.start_time).total_seconds()))
        else:
            entry = await get_next_entry(channel_id, previous_entry, db)
            if not entry:
                # Schedule hasn't been generated this far ahead yet (background
                # scheduler runs nightly). Fall back to a wall-clock lookup so
                # we recover as soon as it catches up, rather than stalling
                # forever waiting for an entry that starts right after the one
                # that just played.
                logger.warning(
                    f"_continuous_stream_generator: channel {channel_id} ran "
                    f"past the end of the generated schedule, falling back "
                    f"to wall-clock lookup"
                )
                entry = await get_current_entry(channel_id, db)
                if entry and entry.id == previous_entry.id:
                    # Nothing has been scheduled after this entry yet and we
                    # already played it in full — don't replay it just
                    # because wall clock still falls inside its old slot.
                    entry = None
                elif entry:
                    now = datetime.now(timezone.utc).replace(tzinfo=None)
                    offset_seconds = max(0, int((now - entry.start_time).total_seconds()))

        if not entry:
            logger.debug(
                f"_continuous_stream_generator: gap on channel {channel_id}, "
                f"waiting {_GAP_POLL_INTERVAL}s"
            )
            await asyncio.sleep(_GAP_POLL_INTERVAL)
            continue

        # Fresh settings for this specific entry — see docstring above.
        channel_result = await db.execute(select(Channel).where(Channel.id == channel_id))
        channel = channel_result.scalar_one_or_none()
        if not channel:
            logger.warning(
                f"_continuous_stream_generator: channel {channel_id} no longer "
                f"exists, ending stream"
            )
            return

        async for chunk in _play_entry(entry, offset_seconds, channel, channel_id, chunk_size):
            yield chunk

        # Advance by playback order, not wall clock — see docstring above.
        # This happens whether the entry played fully or _play_entry bailed
        # out early (bad source, ffmpeg missing) — either way get_next_entry
        # will move past it rather than retrying it forever.
        previous_entry = entry

        # Tiny pause to avoid a tight spin if ffmpeg exits instantly (bad source)
        await asyncio.sleep(0.2)


async def stream_channel(channel_id: int, db: AsyncSession) -> StreamingResponse:
    """
    Start a continuous ffmpeg proxy stream for a channel.

    Verifies that something is scheduled right now (returns 404 otherwise),
    then returns a StreamingResponse backed by _continuous_stream_generator
    which automatically transitions to the next entry when the current one ends.
    """
    logger.info(f"stream_channel: channel_id={channel_id}")

    channel_result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = channel_result.scalar_one_or_none()
    if not channel:
        logger.warning(f"stream_channel: channel {channel_id} not found")
        raise HTTPException(status_code=404, detail="Channel not found")

    # Initial check — return 404 if nothing is playing so clients don't hang
    entry = await get_current_entry(channel_id, db)
    if not entry:
        logger.warning(f"stream_channel: nothing playing on channel {channel_id}")
        raise HTTPException(
            status_code=404, detail="No content scheduled at this time"
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    offset_seconds = max(0, int((now - entry.start_time).total_seconds()))

    return StreamingResponse(
        _continuous_stream_generator(channel_id, db),
        media_type=_MEDIA_TYPE,
        headers={
            "Cache-Control": "no-cache",
            "X-Channel-Id": str(channel_id),
            "X-Entry-Title": entry.title.encode("ascii", errors="replace").decode("ascii"),
            "X-Offset-Seconds": str(offset_seconds),
        },
    )
