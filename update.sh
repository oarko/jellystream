#!/bin/bash
# JellyStream update script
#
# Pulls the latest code from GitHub on the selected channel ("main" =
# stable, "nightly" = latest/may be unstable), reinstalls Python deps if
# requirements.txt changed, and restarts the systemd services if present.
#
# Usage:
#   ./update.sh              # use the channel saved in .env (UPDATE_CHANNEL, default "main")
#   ./update.sh main         # use main for this run and save it to .env
#   ./update.sh nightly      # use nightly for this run and save it to .env
#   ./update.sh -y           # skip the restart confirmation prompt (auto-restart)
#
# Deliberately run by the admin (whoever owns this checkout and has sudo),
# not by the JellyStream service itself — the service account's code tree
# is intentionally read-only (see deploy/README.md "Permissions model");
# this script is how updates actually get applied.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

cd "$(dirname "$0")"

AUTO_YES=0
CHANNEL_ARG=""
for arg in "$@"; do
    case "$arg" in
        -y|--yes) AUTO_YES=1 ;;
        main|nightly) CHANNEL_ARG="$arg" ;;
        *)
            print_error "Unknown argument: $arg"
            echo "Usage: $0 [main|nightly] [-y]"
            exit 1
            ;;
    esac
done

if [ ! -d .git ]; then
    print_error "This doesn't look like a git checkout (no .git directory)."
    print_info "The auto-update feature requires JellyStream to have been installed via 'git clone'."
    exit 1
fi

if ! git remote get-url origin &>/dev/null; then
    print_error "No 'origin' git remote configured — can't determine where to pull from."
    exit 1
fi

# Refuse to touch a dirty working tree. Auto-stashing could silently bury
# someone's in-progress local edits; better to stop and let them decide.
if [ -n "$(git status --porcelain)" ]; then
    print_error "Local changes detected in the working tree — refusing to update."
    print_info "Review with 'git status', then either commit, stash, or discard them first:"
    echo "    git stash push -u          # set changes aside (restore later with: git stash pop)"
    echo "    git checkout -- <file>     # discard changes to one file"
    exit 1
fi

# ── Determine channel ────────────────────────────────────────────────────
_env_get() {
    # Always exits 0 — under `set -e`, a failing command substitution on the
    # right-hand side of an assignment (no .env, or no match) would otherwise
    # silently kill the whole script right here.
    if [ -f .env ]; then
        grep "^$1=" .env | head -1 | cut -d= -f2- || true
    fi
    return 0
}
_env_set() {
    local key="$1" val="$2"
    if [ -f .env ] && grep -q "^${key}=" .env; then
        sed -i "s|^${key}=.*|${key}=${val}|" .env
    else
        echo "${key}=${val}" >> .env
    fi
}

if [ -n "$CHANNEL_ARG" ]; then
    CHANNEL="$CHANNEL_ARG"
    _env_set "UPDATE_CHANNEL" "$CHANNEL"
else
    CHANNEL="$(_env_get UPDATE_CHANNEL)"
    CHANNEL="${CHANNEL:-main}"
fi

if [[ "$CHANNEL" != "main" && "$CHANNEL" != "nightly" ]]; then
    print_error "Invalid channel '$CHANNEL' — must be 'main' or 'nightly'."
    exit 1
fi

print_info "Update channel: ${YELLOW}${CHANNEL}${NC}"

OLD_COMMIT="$(git rev-parse HEAD)"
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

print_info "Fetching from origin..."
git fetch origin

if [ "$CURRENT_BRANCH" != "$CHANNEL" ]; then
    print_info "Switching from '$CURRENT_BRANCH' to '$CHANNEL'..."
    git checkout "$CHANNEL"
fi

print_info "Fast-forwarding to origin/${CHANNEL}..."
if ! git merge --ff-only "origin/${CHANNEL}"; then
    print_error "Can't fast-forward — local '$CHANNEL' has diverged from origin/${CHANNEL}."
    print_info "This shouldn't happen on a clean deployment. Resolve manually, e.g.:"
    echo "    git log --oneline HEAD..origin/${CHANNEL}   # what origin has that you don't"
    echo "    git log --oneline origin/${CHANNEL}..HEAD   # what you have that origin doesn't"
    exit 1
fi

NEW_COMMIT="$(git rev-parse HEAD)"

if [ "$OLD_COMMIT" = "$NEW_COMMIT" ]; then
    print_success "Already up to date (${NEW_COMMIT:0:7}) on '$CHANNEL'."
    exit 0
fi

print_success "Updated ${OLD_COMMIT:0:7} -> ${NEW_COMMIT:0:7} on '$CHANNEL'."

# ── Reinstall dependencies ───────────────────────────────────────────────
if [ -d venv ]; then
    if ! git diff --quiet "$OLD_COMMIT" "$NEW_COMMIT" -- requirements.txt; then
        print_info "requirements.txt changed — reinstalling dependencies..."
        venv/bin/pip install -r requirements.txt
        print_success "Dependencies updated."
    else
        print_info "requirements.txt unchanged — skipping dependency install."
    fi
else
    print_warning "No venv/ found — skipping dependency install. Run ./setup.sh if this is a fresh checkout."
fi

# ── Restart services ──────────────────────────────────────────────────────
# Database schema changes apply automatically on next startup (safe ALTER
# TABLE migrations in app/core/database.py) — a restart is what triggers them.
HAS_SYSTEMD=0
if command -v systemctl &>/dev/null && systemctl list-unit-files jellystream-api.service &>/dev/null; then
    HAS_SYSTEMD=1
fi

if [ "$HAS_SYSTEMD" -eq 1 ]; then
    if [ "$AUTO_YES" -eq 1 ]; then
        DO_RESTART=1
    else
        read -p "Restart jellystream-api and jellystream-web now? (Y/n): " -n 1 -r
        echo
        DO_RESTART=1
        [[ $REPLY =~ ^[Nn]$ ]] && DO_RESTART=0
    fi

    if [ "$DO_RESTART" -eq 1 ]; then
        print_info "Restarting services..."
        sudo systemctl restart jellystream-api.service
        sudo systemctl restart jellystream-web.service 2>/dev/null || true
        print_success "Services restarted."
    else
        print_warning "Not restarted — changes won't take effect until you run:"
        echo "    sudo systemctl restart jellystream-api jellystream-web"
    fi
else
    print_warning "No systemd units found — if JellyStream is running via ./start.sh, restart it manually to pick up the update."
fi

print_success "Update complete."
