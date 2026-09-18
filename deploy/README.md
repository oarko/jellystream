# Running JellyStream as a systemd service

Two services, mirroring the two dev scripts:

| Script              | systemd unit               | Does |
|----------------------|-----------------------------|------|
| `start.sh`           | `jellystream-api.service`  | FastAPI backend (`run.py` via the venv) |
| `start-lighttpd.sh`  | `jellystream-web.service`  | PHP frontend (Lighttpd + FastCGI) |

Both units assume the project lives at `/home/oarko/jellystream` and run as
a dedicated **`jellystream` system user** (no login, no home directory) —
`./setup.sh` creates this user automatically (see below). **Edit
`WorkingDirectory=`, `ExecStart=`, `User=` and `Group=` in both `.service`
files first if the project path differs on this machine, or if you chose
not to create the dedicated user.**

## Prerequisites

- `./setup.sh` has already been run at least once. As of this version, it:
  - creates `venv/`, installs Python deps
  - interactively asks for the handful of `.env` settings every install
    needs (Jellyfin URL/API key, JellyStream's public URL, etc.), with
    examples — no more hand-editing `.env` or relying on the web setup
    wizard for first-time config
  - creates the `jellystream` system user these services run as, and adds
    it to the `render`/`video` groups (whichever exist on this machine) so
    GPU-accelerated transcoding (the channel Hardware Acceleration setting)
    works out of the box
  - sets permissions so `jellystream` can read the whole project tree and
    write `data/` + `logs/` — see "Permissions model" below
  - also adds *you* (whoever ran the script) to the `jellystream` group, so
    you can read logs/the database without `sudo`. **Log out and back in
    (or run `newgrp jellystream`) for that to take effect.**
- For the web service: `lighttpd`, `php-cgi`, `php-sqlite3`, `php-curl`,
  `php-json` are installed (`setup.sh` offers to do this).
- `DEBUG=False` in `.env` — with `DEBUG=True`, `run.py` starts uvicorn with
  auto-reload, which manages its own subprocess and complicates how cleanly
  systemd can stop/restart it. Fine for dev, not for a service.
- If your media library lives outside this project directory (the usual
  case), make sure `jellystream` can actually read it — `setup.sh` can't
  automate this part since it doesn't know your media layout. Add the user
  to whatever group owns those files, or adjust the mount's permissions.
- Re-ran `setup.sh` on a machine where `jellystream` already existed, or
  changed which groups exist (e.g. installed GPU drivers afterward)? It's
  idempotent — safe to run again; it'll pick up the new group and skip
  recreating the user.

## Permissions model

`setup.sh` group-owns the whole project tree by `jellystream` with
**read+execute only** (`chgrp -R` + `chmod -R g+rX`) — it does not change
who *owns* anything, so the account that ran setup keeps full control.
Only `data/` and `logs/` get group **write** too, since those are the only
things the running services actually need to write. Two narrow exceptions:
`.env` and `app/web/php/.phpconfig` also get group write, so the web
frontend's own setup wizard (`setup.php`) — which runs as this same service
user, under lighttpd/PHP-CGI — can still save changes there. Everything
else in the tree (code, the venv) stays read-only for the service user.

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
