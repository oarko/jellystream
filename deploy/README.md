# Running JellyStream as a systemd service

Two services, mirroring the two dev scripts:

| Script              | systemd unit               | Does |
|----------------------|-----------------------------|------|
| `start.sh`           | `jellystream-api.service`  | FastAPI backend (`run.py` via the venv) |
| `start-lighttpd.sh`  | `jellystream-web.service`  | PHP frontend (Lighttpd + FastCGI) |

Both units assume the project lives at `/home/oarko/jellystream` and runs as
user `oarko`. **Edit `WorkingDirectory=`, `ExecStart=`, `User=` and `Group=`
in both `.service` files first if either differs on this machine.**

## Prerequisites

- `./setup.sh` has already been run at least once (creates `venv/`, installs
  Python deps, creates `.env`).
- For the web service: `lighttpd`, `php-cgi`, `php-sqlite3`, `php-curl`,
  `php-json` are installed (`setup.sh` offers to do this).
- `DEBUG=False` in `.env` — with `DEBUG=True`, `run.py` starts uvicorn with
  auto-reload, which manages its own subprocess and complicates how cleanly
  systemd can stop/restart it. Fine for dev, not for a service.
- If you're using GPU-accelerated transcoding (`hwaccel` on any channel):
  the user the API service runs as must be in the `render` (and usually
  `video`) group, e.g. `sudo usermod -aG render,video oarko`. Group changes
  only take effect for processes started *after* the change — restart the
  service (not just `daemon-reload`) once you've done this.

## Install

```bash
sudo cp deploy/systemd/jellystream-api.service /etc/systemd/system/
sudo cp deploy/systemd/jellystream-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now jellystream-api.service
sudo systemctl enable --now jellystream-web.service
```

Check status and logs:

```bash
systemctl status jellystream-api.service jellystream-web.service
journalctl -u jellystream-api -f      # live-tail the API
journalctl -u jellystream-web -f      # live-tail the frontend
```

The API's own detailed log still lands in `./logs/jellystream_*.log` as
before (see the Logging section below) — the journal is just a convenient
second place to watch it live, and only holds what got sent to stdout.

## Log management

**API backend** — already had this before today: `.env`'s
`LOG_FILE_MAX_BYTES` / `LOG_FILE_BACKUP_COUNT` / `LOG_RETENTION_DAYS` control
size-based rotation and how long rotated files are kept. New: set
`LOG_TO_CONSOLE=False` in `.env` to stop also duplicating every line to
stdout/the journal, if you don't want two copies.

**PHP frontend** — Lighttpd has no built-in size rotation for
`logs/lighttpd-access.log` / `logs/lighttpd-error.log`, so this ships a
`logrotate` rule instead, which is the standard Linux tool for exactly this
(already installed on virtually every Debian/Ubuntu system):

```bash
sudo cp deploy/logrotate/jellystream-web /etc/logrotate.d/jellystream-web
sudo logrotate -d /etc/logrotate.d/jellystream-web   # dry run — shows what it would do
```

It rotates at 10MB or weekly (whichever comes first), keeps 8 rotated
files, and compresses old ones. Edit the paths inside that file first if
JellyStream isn't at `/home/oarko/jellystream` here.

## Stopping / restarting

```bash
sudo systemctl restart jellystream-api.service
sudo systemctl restart jellystream-web.service
sudo systemctl stop jellystream-api.service jellystream-web.service
```

`start-lighttpd.sh` was tweaked to `exec` into `lighttpd` at the end instead
of running it as a child process, so `systemctl stop`/`restart` reliably
stops the actual lighttpd process rather than only the wrapper script.
