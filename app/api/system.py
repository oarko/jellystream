"""
System/version info and update-availability check.

Deliberately read-only. The running service's own code tree is intentionally
NOT writable by the account these endpoints run under (see deploy/README.md
"Permissions model") — actually applying an update means pulling new code,
which is done by running ./update.sh as the admin (who owns the tree), not
by this process. These endpoints only report current version info and
whether something newer exists upstream, plus persist which branch
("main" | "nightly") that check/update.sh should use.
"""

import asyncio
import re
from pathlib import Path
from typing import Optional

import aiohttp
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALID_CHANNELS = {"main", "nightly"}

# Used only as a last-resort fallback if the local git remote can't be read
# (e.g. no .git directory in a non-git deployment) — the real value is
# normally derived from `git remote get-url origin` below.
_FALLBACK_REPO_SLUG = "oarko/jellystream"

# In-memory override so a channel change via PUT is reflected immediately
# by subsequent GETs in this process, without needing a restart. Still
# persisted to .env (below) so it survives one.
_channel_override: Optional[str] = None


def _current_channel() -> str:
    return _channel_override or settings.UPDATE_CHANNEL or "main"


async def _run_git(*args: str) -> Optional[str]:
    """Run a read-only git command in the project root; None on any failure."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            cwd=str(PROJECT_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
        if proc.returncode != 0:
            return None
        return stdout.decode().strip()
    except Exception as exc:
        logger.debug(f"_run_git: git {' '.join(args)} failed: {exc}")
        return None


async def _repo_slug() -> str:
    """Derive 'owner/repo' from the origin remote URL; falls back if unreadable."""
    url = await _run_git("remote", "get-url", "origin")
    if not url:
        return _FALLBACK_REPO_SLUG
    # Matches both "https://github.com/owner/repo.git" and "git@github.com:owner/repo.git"
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url.strip())
    return m.group(1) if m else _FALLBACK_REPO_SLUG


class UpdateChannelRequest(BaseModel):
    channel: str  # "main" | "nightly"


@router.get("/version")
async def get_version():
    """Current git branch/commit/dirty state and the configured update channel."""
    logger.debug("get_version called")
    branch = await _run_git("rev-parse", "--abbrev-ref", "HEAD")
    commit = await _run_git("rev-parse", "HEAD")
    commit_short = await _run_git("rev-parse", "--short", "HEAD")
    commit_date = await _run_git("log", "-1", "--format=%cI", "HEAD")
    dirty_output = await _run_git("status", "--porcelain")

    git_available = commit is not None
    return {
        "git_available": git_available,
        "branch": branch,
        "commit": commit,
        "commit_short": commit_short,
        "commit_date": commit_date,
        "dirty": bool(dirty_output) if git_available else None,
        "channel": _current_channel(),
    }


@router.get("/update-check")
async def check_for_updates(channel: Optional[str] = None):
    """
    Compare local HEAD against the tip of the given (or configured) branch
    on GitHub. Uses GitHub's public REST API — no local git fetch, so this
    never touches the working tree or needs write access to .git.
    """
    target_channel = channel or _current_channel()
    if target_channel not in VALID_CHANNELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid channel '{target_channel}'. Must be one of: {sorted(VALID_CHANNELS)}",
        )

    local_commit = await _run_git("rev-parse", "HEAD")
    if local_commit is None:
        raise HTTPException(
            status_code=503,
            detail="Could not read local git state — is this a git checkout?",
        )

    slug = await _repo_slug()
    url = f"https://api.github.com/repos/{slug}/commits/{target_channel}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "JellyStream-UpdateCheck",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning(f"check_for_updates: GitHub API returned {resp.status}: {body[:200]}")
                    raise HTTPException(
                        status_code=503,
                        detail=f"GitHub API returned {resp.status} for {slug}@{target_channel}",
                    )
                data = await resp.json()
    except aiohttp.ClientError as exc:
        logger.warning(f"check_for_updates: network error reaching GitHub: {exc}")
        raise HTTPException(status_code=503, detail=f"Could not reach GitHub: {exc}")

    latest_sha = data.get("sha", "")
    latest_date = (
        data.get("commit", {}).get("committer", {}).get("date")
        or data.get("commit", {}).get("author", {}).get("date")
    )
    latest_message = (data.get("commit", {}).get("message") or "").split("\n")[0]

    logger.info(
        f"check_for_updates: channel={target_channel} local={local_commit[:7]} "
        f"latest={latest_sha[:7] if latest_sha else '?'}"
    )
    return {
        "channel": target_channel,
        "local_commit": local_commit,
        "local_commit_short": local_commit[:7],
        "latest_commit": latest_sha,
        "latest_commit_short": latest_sha[:7] if latest_sha else None,
        "latest_commit_date": latest_date,
        "latest_commit_message": latest_message,
        "update_available": bool(latest_sha) and latest_sha != local_commit,
    }


@router.put("/update-channel")
async def set_update_channel(req: UpdateChannelRequest):
    """Persist which branch ('main' | 'nightly') future checks/update.sh should use."""
    global _channel_override
    logger.debug(f"set_update_channel: channel={req.channel!r}")
    if req.channel not in VALID_CHANNELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid channel '{req.channel}'. Must be one of: {sorted(VALID_CHANNELS)}",
        )

    _update_env_file("UPDATE_CHANNEL", req.channel)
    _channel_override = req.channel
    logger.info(f"set_update_channel: channel set to {req.channel!r}")
    return {"message": "Update channel saved", "channel": req.channel}


def _update_env_file(key: str, value: str) -> None:
    """
    Set (or append) one KEY=value line in .env, leaving every other line —
    comments included — untouched. Mirrors setup.sh's _env_set, which exists
    because a full-file rewrite has previously mangled unrelated values.
    """
    env_path = PROJECT_ROOT / ".env"
    pattern = re.compile(rf"^{re.escape(key)}=.*$")

    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n")
        return

    lines = env_path.read_text().splitlines(keepends=True)
    for i, line in enumerate(lines):
        if pattern.match(line.rstrip("\n")):
            lines[i] = f"{key}={value}\n"
            env_path.write_text("".join(lines))
            return

    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    lines.append(f"{key}={value}\n")
    env_path.write_text("".join(lines))
