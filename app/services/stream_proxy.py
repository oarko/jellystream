"""ffmpeg-based stream proxy.

One shared pipeline per channel: the first viewer starts it, later viewers
attach to the same live MPEG-TS stream instead of spawning another ffmpeg,
and it stops shortly after the last viewer leaves. The pipeline plays the
channel's schedule entry by entry (joining the current one at the correct
offset, like real TV) and starts the next entry's ffmpeg just before the
current one ends so there is no gap at the boundary. See _ChannelHub.
"""

import asyncio
import json
import os
import time
from asyncio.subprocess import PIPE
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
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

    Used by _ChannelHub to advance from one entry to the next by playback
    order rather than by re-deriving position from "now" — see
    _ChannelHub._plan_next for why that distinction matters.
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
    output_ts_offset: float = 0.0,
) -> list:
    """
    Build the ffmpeg command for one schedule entry.

    Always includes -re (read input at native frame rate). Without it,
    ffmpeg decodes/encodes as fast as the hardware allows — not at 1x
    playback speed — and the only thing that happens to slow it down to
    roughly real-time is TCP/pipe backpressure from however fast the
    downstream client happens to be reading. That's not reliable: a client
    that buffers ahead aggressively (common for live-TV style playback) lets
    ffmpeg race through an entire file in minutes. From ffmpeg's side that's
    a completely normal, clean finish — it really did reach EOF — so
    _Segment has no way to tell that apart from a genuine finish, and the
    schedule advances immediately, looking exactly like the channel
    "jumping ahead" through content far faster than anyone could be
    watching it.

    output_ts_offset: seconds added to every output timestamp. Each schedule
        entry is a separate ffmpeg process whose MPEG-TS timestamps would
        otherwise restart near zero, so the client sees the timeline jump
        backwards at every item boundary — which ffmpeg-based players (incl.
        Jellyfin's own live-TV pipeline) commonly fail on. _ChannelHub passes
        the running total of everything already sent on the channel so the
        timeline keeps moving forward across items.

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
        decode always produces regardless of the source format. _Segment
        always uses hw_decode=False for this reason (a GPU can also decode a
        file into silently corrupted frames, which can't be detected).
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
        "-re",                         # read the input at its native frame rate
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
    # A keyframe every 2s: a viewer joining an already-running stream can only
    # start decoding at one, so this bounds how long they wait.
    cmd += ["-force_key_frames", "expr:gte(t,n_forced*2)"]
    cmd += ["-maxrate", "8000k", "-bufsize", "4000k"]

    # ── Audio — AAC stereo ────────────────────────────────────────────────
    cmd += [
        "-c:a", "aac",
        "-b:a", "192k",
        "-ac", "2",                    # downmix to stereo
    ]
    if output_ts_offset > 0:
        cmd += ["-output_ts_offset", f"{output_ts_offset:.3f}"]
    cmd += [
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


async def _probe_duration(source: str) -> Optional[float]:
    """Return the container duration in seconds via ffprobe, or None."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            source,
            stdout=PIPE, stderr=PIPE,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            await proc.wait()
            logger.warning(f"_probe_duration: ffprobe timed out for {source!r}")
            return None
        value = float(stdout.decode().strip())
        return value if value > 0 else None
    except Exception as exc:
        logger.debug(f"_probe_duration: could not determine duration: {exc}")
        return None


# ── Shared per-channel streaming ─────────────────────────────────────────────
#
# One ChannelHub per channel that has at least one viewer. It owns the only
# ffmpeg pipeline for that channel and fans the resulting MPEG-TS out to every
# connected viewer, so a second device watching the same channel joins the
# live stream where it currently is (like real TV) instead of spawning a
# second encode. Each schedule entry is a _Segment (one ffmpeg process); the
# next segment is started a few seconds before the current one ends so its
# first frames are already waiting at the boundary.

_TS_PACKET = 188
_TS_CHUNK = _TS_PACKET * 348            # ~64 KB — always a whole number of TS packets, so a
                                        # viewer joining at any chunk starts on a packet boundary
_SEGMENT_QUEUE_CHUNKS = 200             # ~12 MB of look-ahead per segment
_SUBSCRIBER_QUEUE_CHUNKS = 400          # ~25 MB per viewer before it's dropped as too slow
_PREROLL_SECONDS = 3.0                  # start the next ffmpeg this long before the current one ends
_PREPARE_SECONDS = 12.0                 # look up/probe the next entry this long before it ends
_HUB_IDLE_GRACE = 15.0                  # keep the pipeline alive this long after the last viewer leaves
_IDLE = object()

_hubs: dict = {}


class _ChannelGone(Exception):
    """The channel row no longer exists."""


class _TranscodeSettings:
    """Plain snapshot of a channel's transcode settings (no ORM object)."""

    __slots__ = ("max_height", "preset", "hwaccel", "hwaccel_device")

    def __init__(self, channel: Channel):
        self.max_height = channel.transcode_max_height
        self.preset = channel.transcode_preset or "veryfast"
        self.hwaccel = channel.hwaccel or "none"
        self.hwaccel_device = channel.hwaccel_device


class _Segment:
    """
    One schedule entry being encoded by ffmpeg into a bounded queue of
    TS-aligned chunks. A trailing None marks a normal end. The queue's bound
    is also the backpressure: ffmpeg blocks (via its pipe) instead of racing
    ahead if nothing is consuming.

    Tries, in order — the second only if the first produced no output or
    exited abnormally:
      1. software decode + hardware encode (skipped when hwaccel is "none")
         Hardware DECODE is deliberately never attempted: a GPU driver can
         "successfully" decode a file into corrupted frames — no error, clean
         exit code — and nothing here could detect that.
      2. full software (libx264)
    """

    def __init__(self, entry, offset_seconds, settings, channel_id, source,
                 audio_idx, expected_media, ts_offset):
        self.entry = entry
        self.offset_seconds = offset_seconds
        self.settings = settings
        self.channel_id = channel_id
        self.source = source
        self.audio_idx = audio_idx
        self.expected_media = expected_media   # media seconds this run will produce, or None
        self.ts_offset = ts_offset             # first timestamp of this segment's output
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=_SEGMENT_QUEUE_CHUNKS)
        self.proc_started = time.monotonic()
        self.wall_elapsed = 0.0
        self.clean = False
        self.task = asyncio.create_task(self._run())

    def remaining(self) -> Optional[float]:
        """Seconds of media still to be produced, or None if the length is unknown."""
        if self.expected_media is None:
            return None
        return self.expected_media - (time.monotonic() - self.proc_started)

    def end_offset(self) -> float:
        """Where the next segment's timestamps should begin so the timeline never steps backwards."""
        # While still running (the early-start case) the only number available
        # is the predicted length; once finished, a clean run is exactly that
        # length and anything else falls back to how long it actually ran.
        if self.expected_media is not None and (self.clean or not self.task.done()):
            media = self.expected_media
        else:
            media = self.wall_elapsed
        return self.ts_offset + media + 0.3

    async def cancel(self) -> None:
        self.task.cancel()
        try:
            await self.task
        except (asyncio.CancelledError, Exception):
            pass

    async def _run(self) -> None:
        try:
            await self._run_stages()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                f"_Segment: unexpected error playing '{self.entry.title}': {exc}",
                exc_info=True,
            )
        await self.queue.put(None)

    async def _run_stages(self) -> None:
        s = self.settings
        hwaccel = s.hwaccel
        stages = [("none", True)] if hwaccel == "none" else [(hwaccel, False), ("none", True)]

        for stage_index, (stage_hwaccel, hw_decode) in enumerate(stages):
            is_last_stage = stage_index == len(stages) - 1
            cmd = _build_ffmpeg_cmd(
                self.source, self.offset_seconds, self.audio_idx,
                max_height=s.max_height,
                preset=s.preset,
                hwaccel=stage_hwaccel,
                hwaccel_device=s.hwaccel_device,
                hw_decode=hw_decode,
                output_ts_offset=self.ts_offset,
            )
            logger.debug(
                f"_Segment: starting ffmpeg for '{self.entry.title}' (id={self.entry.id}), "
                f"offset={self.offset_seconds}s, hwaccel={stage_hwaccel}, hw_decode={hw_decode}, "
                f"ts_offset={self.ts_offset:.1f}s, "
                f"audio_stream={self.audio_idx if self.audio_idx is not None else 'default'}"
            )

            try:
                process = await asyncio.create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
            except FileNotFoundError:
                logger.error("_Segment: ffmpeg not found")
                return
            self.proc_started = time.monotonic()

            stderr_tail = bytearray()
            stderr_task = asyncio.create_task(_drain_stderr(process, stderr_tail))
            sent = 0
            buf = bytearray()
            try:
                while True:
                    data = await process.stdout.read(65536)
                    if not data:
                        break
                    buf += data
                    while len(buf) >= _TS_CHUNK:
                        await self.queue.put(bytes(buf[:_TS_CHUNK]))
                        del buf[:_TS_CHUNK]
                        sent += _TS_CHUNK
                # Flush whole packets; a trailing partial packet (a killed
                # process) is dropped so the stream stays packet-aligned.
                usable = len(buf) - (len(buf) % _TS_PACKET)
                if usable:
                    await self.queue.put(bytes(buf[:usable]))
                    sent += usable
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

            self.wall_elapsed = time.monotonic() - self.proc_started
            returncode = process.returncode

            # A clean finish needs BOTH output AND a zero exit code: a process
            # killed part-way (e.g. OOM) still closes its pipe, which looks
            # like a normal EOF if only the byte count is checked.
            if sent > 0 and returncode == 0:
                self.clean = True
                logger.info(
                    f"_Segment: channel={self.channel_id} '{self.entry.title}' finished "
                    f"(hwaccel={stage_hwaccel}, hw_decode={hw_decode}, bytes={sent})"
                )
                return

            if is_last_stage:
                logger.error(
                    f"_Segment: channel={self.channel_id} '{self.entry.title}' gave up after "
                    f"exhausting all fallback tiers (hwaccel={stage_hwaccel}, hw_decode={hw_decode}, "
                    f"returncode={returncode}, bytes={sent}) — moving on to the next scheduled "
                    f"entry. ffmpeg stderr tail: {bytes(stderr_tail)[-2000:]!r}"
                )
                return

            if sent > 0:
                # Some output already went to viewers; the retry must continue
                # after it on the timeline rather than restart underneath it.
                self.ts_offset += self.wall_elapsed + 0.5
            logger.error(
                f"_Segment: hwaccel={stage_hwaccel} hw_decode={hw_decode} "
                f"{'produced no output' if sent == 0 else f'exited abnormally (returncode={returncode}) after {sent} bytes'} "
                f"for '{self.entry.title}' (channel={self.channel_id}), trying next fallback "
                f"stage. ffmpeg stderr tail: {bytes(stderr_tail)[-2000:]!r}"
            )


class _Subscriber:
    __slots__ = ("queue",)

    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=_SUBSCRIBER_QUEUE_CHUNKS)


def _close_subscriber(sub: "_Subscriber") -> None:
    """Discard anything buffered and tell the viewer's response to end."""
    try:
        while True:
            sub.queue.get_nowait()
    except asyncio.QueueEmpty:
        pass
    sub.queue.put_nowait(None)


class _ChannelHub:
    """The single ffmpeg pipeline for one channel, shared by all its viewers."""

    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        self.subscribers: set = set()
        self.task: Optional[asyncio.Task] = None
        self.alive = True
        self.current_title: Optional[str] = None
        self._idle_handle = None

    # ── viewers ──────────────────────────────────────────────────────────────

    def subscribe(self) -> _Subscriber:
        sub = _Subscriber()
        self.subscribers.add(sub)
        if self._idle_handle is not None:
            self._idle_handle.cancel()
            self._idle_handle = None
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self._produce())
        logger.info(
            f"ChannelHub {self.channel_id}: viewer joined ({len(self.subscribers)} watching)"
        )
        return sub

    def unsubscribe(self, sub: _Subscriber) -> None:
        self.subscribers.discard(sub)
        logger.info(
            f"ChannelHub {self.channel_id}: viewer left ({len(self.subscribers)} watching)"
        )
        if not self.subscribers and self.alive and self._idle_handle is None:
            self._idle_handle = asyncio.get_running_loop().call_later(
                _HUB_IDLE_GRACE, self._stop_if_idle
            )

    def _stop_if_idle(self) -> None:
        self._idle_handle = None
        if not self.subscribers and self.task and not self.task.done():
            logger.info(
                f"ChannelHub {self.channel_id}: no viewers for {_HUB_IDLE_GRACE:.0f}s, stopping"
            )
            self.task.cancel()

    def _broadcast(self, chunk: bytes) -> None:
        for sub in list(self.subscribers):
            try:
                sub.queue.put_nowait(chunk)
            except asyncio.QueueFull:
                # Dropping chunks would break packet alignment, so a viewer
                # that can't keep up is disconnected (it can simply reconnect).
                logger.warning(
                    f"ChannelHub {self.channel_id}: dropping a viewer that fell too far behind"
                )
                self.subscribers.discard(sub)
                _close_subscriber(sub)

    # ── schedule lookup ──────────────────────────────────────────────────────

    async def _plan_next(self, previous_entry):
        """
        Pick the next entry to play. Returns (entry, offset_seconds, settings),
        or None if nothing is scheduled. Raises _ChannelGone if the channel
        was deleted.

        The first entry is chosen by wall clock, so someone tuning in lands
        mid-show like real TV. Every entry after that follows playback order
        and starts at 0 — schedule lengths come from Jellyfin's reported
        runtime, which can differ slightly from the real file, and re-deriving
        position from the clock would skip or repeat content. If nothing is
        scheduled after the previous entry this returns None (a gap).
        """
        offset_seconds = 0
        # Short-lived session per lookup: holding one for the life of a
        # stream (hours) leaks pooled connections, and the ORM would keep
        # returning an already-loaded (stale) Channel from its identity map.
        async with AsyncSessionLocal() as session:
            if previous_entry is None:
                entry = await get_current_entry(self.channel_id, session)
                if entry:
                    now = datetime.now(timezone.utc).replace(tzinfo=None)
                    offset_seconds = max(0, int((now - entry.start_time).total_seconds()))
            else:
                # No wall-clock fallback here: if nothing starts after the previous
                # entry, a clock lookup can only return that same entry or an
                # earlier one (this pipeline plays slightly ahead of the clock),
                # i.e. a replay. Report a gap instead; the caller keeps polling
                # until the nightly job extends the schedule.
                entry = await get_next_entry(self.channel_id, previous_entry, session)

            if not entry:
                return None

            result = await session.execute(select(Channel).where(Channel.id == self.channel_id))
            channel = result.scalar_one_or_none()
            if channel is None:
                raise _ChannelGone()
            return entry, offset_seconds, _TranscodeSettings(channel)

    async def _prepare(self, entry, offset_seconds):
        """Resolve the source and probe it. Returns (source, audio_idx, expected_media) or None."""
        try:
            source = await _resolve_source(entry, self.channel_id)
        except Exception as exc:
            logger.error(
                f"ChannelHub {self.channel_id}: could not resolve source for entry "
                f"{entry.id} '{entry.title}': {exc}",
                exc_info=True,
            )
            return None
        audio_idx, duration = await asyncio.gather(
            _detect_preferred_audio_index(source), _probe_duration(source)
        )
        if duration is None and getattr(entry, "duration", None):
            duration = float(entry.duration)
        expected = max(0.0, duration - offset_seconds) if duration else None
        return source, audio_idx, expected

    async def _prepare_next(self, cur: _Segment) -> Optional[_Segment]:
        """
        Look up and probe the entry after `cur`, wait until it's nearly time,
        then launch its ffmpeg so its first output is already buffered when
        `cur` ends. Returns None if there's nothing to pre-start.
        """
        plan = await self._plan_next(cur.entry)
        if plan is None:
            return None
        entry, offset_seconds, settings = plan
        prepared = await self._prepare(entry, offset_seconds)
        if prepared is None:
            return None
        source, audio_idx, expected = prepared

        wait = (cur.remaining() or 0.0) - _PREROLL_SECONDS
        if wait > 0:
            await asyncio.sleep(wait)
        return _Segment(
            entry, offset_seconds, settings, self.channel_id, source, audio_idx,
            expected, ts_offset=cur.end_offset(),
        )

    # ── the pipeline ─────────────────────────────────────────────────────────

    async def _produce(self) -> None:
        cur: Optional[_Segment] = None
        next_task: Optional[asyncio.Task] = None
        previous_entry = None
        ts_offset = 0.0
        gap_logged = False
        logger.info(f"ChannelHub {self.channel_id}: pipeline started")
        try:
            while True:
                if cur is None:
                    try:
                        plan = await self._plan_next(previous_entry)
                    except _ChannelGone:
                        logger.warning(f"ChannelHub {self.channel_id}: channel deleted, stopping")
                        return
                    if plan is None:
                        if not gap_logged:
                            logger.warning(
                                f"ChannelHub {self.channel_id}: nothing scheduled after the "
                                f"last entry (schedule needs extending); polling every "
                                f"{_GAP_POLL_INTERVAL}s"
                            )
                            gap_logged = True
                        await asyncio.sleep(_GAP_POLL_INTERVAL)
                        continue
                    gap_logged = False
                    entry, offset_seconds, settings = plan
                    prepared = await self._prepare(entry, offset_seconds)
                    if prepared is None:
                        previous_entry = entry      # skip an entry we can't open
                        await asyncio.sleep(2)
                        continue
                    source, audio_idx, expected = prepared
                    cur = _Segment(entry, offset_seconds, settings, self.channel_id,
                                   source, audio_idx, expected, ts_offset)

                self.current_title = cur.entry.title
                logger.info(
                    f"ChannelHub {self.channel_id}: now playing '{cur.entry.title}' "
                    f"(id={cur.entry.id}, offset={cur.offset_seconds}s)"
                )

                # Forward this segment to every viewer until it ends.
                while True:
                    try:
                        chunk = await asyncio.wait_for(cur.queue.get(), timeout=0.5)
                    except asyncio.TimeoutError:
                        chunk = _IDLE
                    if chunk is None:
                        break
                    if chunk is _IDLE:
                        if cur.task.done() and cur.queue.empty():
                            break
                    else:
                        self._broadcast(chunk)

                    if next_task is None:
                        remaining = cur.remaining()
                        if remaining is not None and remaining <= _PREPARE_SECONDS:
                            next_task = asyncio.create_task(self._prepare_next(cur))

                # This segment is over: pick up where it left off. Let it finish
                # settling first so its final numbers (clean / elapsed) are set.
                await asyncio.wait({cur.task}, timeout=5.0)
                previous_entry = cur.entry
                ts_offset = cur.end_offset()
                cur = None
                if next_task is not None:
                    try:
                        cur = await next_task
                    except _ChannelGone:
                        return
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        logger.error(
                            f"ChannelHub {self.channel_id}: preparing the next entry failed: {exc}",
                            exc_info=True,
                        )
                        cur = None
                    next_task = None
                await asyncio.sleep(0)   # yield so a burst never starves other tasks
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(f"ChannelHub {self.channel_id}: pipeline crashed: {exc}", exc_info=True)
        finally:
            self.alive = False
            if _hubs.get(self.channel_id) is self:
                del _hubs[self.channel_id]
            if next_task is not None:
                if not next_task.done():
                    next_task.cancel()
                    try:
                        await next_task
                    except (asyncio.CancelledError, Exception):
                        pass
                elif not next_task.cancelled() and next_task.exception() is None:
                    pending = next_task.result()
                    if pending is not None:
                        await pending.cancel()
            if cur is not None:
                await cur.cancel()
            for sub in list(self.subscribers):
                _close_subscriber(sub)
            self.subscribers.clear()
            if self._idle_handle is not None:
                self._idle_handle.cancel()
            logger.info(f"ChannelHub {self.channel_id}: pipeline stopped")


async def _subscriber_stream(hub: _ChannelHub, sub: _Subscriber):
    try:
        while True:
            chunk = await sub.queue.get()
            if chunk is None:
                break
            yield chunk
    finally:
        hub.unsubscribe(sub)


async def shutdown_streams() -> None:
    """Stop every channel pipeline (and its ffmpeg processes). Called on app shutdown."""
    tasks = [h.task for h in list(_hubs.values()) if h.task and not h.task.done()]
    for t in tasks:
        t.cancel()
    for t in tasks:
        try:
            await t
        except (asyncio.CancelledError, Exception):
            pass


async def stream_channel(channel_id: int, db: AsyncSession) -> StreamingResponse:
    """
    Attach the caller to a channel's live stream, starting the channel's
    ffmpeg pipeline if nobody is watching it yet. A second (third, ...) viewer
    joins the existing pipeline at its current position rather than starting
    another encode.
    """
    logger.info(f"stream_channel: channel_id={channel_id}")

    hub = _hubs.get(channel_id)
    title = hub.current_title if hub and hub.alive else None
    offset_header = "live"

    if hub is None or not hub.alive:
        channel_result = await db.execute(select(Channel).where(Channel.id == channel_id))
        if channel_result.scalar_one_or_none() is None:
            logger.warning(f"stream_channel: channel {channel_id} not found")
            raise HTTPException(status_code=404, detail="Channel not found")

        # Return 404 up front if nothing is playing so clients don't hang.
        entry = await get_current_entry(channel_id, db)
        if not entry:
            logger.warning(f"stream_channel: nothing playing on channel {channel_id}")
            raise HTTPException(status_code=404, detail="No content scheduled at this time")
        title = entry.title
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        offset_header = str(max(0, int((now - entry.start_time).total_seconds())))

        # Re-check: another request may have created the hub while we awaited.
        hub = _hubs.get(channel_id)
        if hub is None or not hub.alive:
            hub = _ChannelHub(channel_id)
            _hubs[channel_id] = hub

    sub = hub.subscribe()
    return StreamingResponse(
        _subscriber_stream(hub, sub),
        media_type=_MEDIA_TYPE,
        headers={
            "Cache-Control": "no-cache",
            "X-Channel-Id": str(channel_id),
            "X-Entry-Title": (title or "").encode("ascii", errors="replace").decode("ascii"),
            "X-Offset-Seconds": offset_header,
        },
    )
