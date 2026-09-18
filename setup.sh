#!/bin/bash
# JellyStream Setup Script
# Handles virtual environment setup on Debian/Ubuntu and other Linux distributions

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VENV_NAME="venv"
PYTHON_CMD="python3"
MIN_PYTHON_VERSION="3.11"

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════╗"
echo "║     JellyStream Setup Script              ║"
echo "╚═══════════════════════════════════════════╝"
echo -e "${NC}"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is installed
check_python() {
    print_info "Checking Python installation..."

    if ! command -v $PYTHON_CMD &> /dev/null; then
        print_error "Python 3 is not installed!"
        print_info "Please install Python 3.11 or higher first:"
        echo "  sudo apt install python3 python3-pip python3-venv"
        exit 1
    fi

    # Get Python version
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    print_success "Found Python $PYTHON_VERSION"

    # Check if version meets minimum requirement
    if ! $PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
        print_warning "Python version $PYTHON_VERSION detected. Python $MIN_PYTHON_VERSION or higher is recommended."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Detect OS and check for required packages
check_system_requirements() {
    print_info "Detecting operating system..."

    # Detect OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
        print_success "Detected: $NAME $VERSION"
    else
        print_warning "Could not detect OS. Proceeding with generic setup..."
        OS="unknown"
    fi

    # Check for Debian/Ubuntu specific requirements
    if [[ "$OS" == "debian" ]] || [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "kubuntu" ]]; then
        print_info "Checking for python3-venv package..."

        if ! dpkg -l | grep -q python3-venv; then
            print_warning "python3-venv package not found!"
            print_info "This package is required on Debian-based systems."

            read -p "Install python3-venv now? (Y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                print_info "Installing python3-venv..."
                sudo apt update
                sudo apt install -y python3-venv
                print_success "python3-venv installed successfully!"
            else
                print_error "Cannot proceed without python3-venv. Exiting."
                exit 1
            fi
        else
            print_success "python3-venv is already installed"
        fi

        # Check for python3-dev (useful for some packages)
        if ! dpkg -l | grep -q python3-dev; then
            print_info "python3-dev is recommended for building some packages"
            read -p "Install python3-dev? (Y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                sudo apt install -y python3-dev
            fi
        fi

        # Check for ffmpeg (required for stream proxy and audio detection)
        print_info "Checking for ffmpeg..."
        if ! command -v ffmpeg &> /dev/null || ! command -v ffprobe &> /dev/null; then
            print_warning "ffmpeg / ffprobe not found — required for stream proxy and audio detection"
            read -p "Install ffmpeg now? (Y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                print_info "Installing ffmpeg..."
                sudo apt install -y ffmpeg
                print_success "ffmpeg installed!"
            else
                print_warning "Skipping ffmpeg. Streams will not work until ffmpeg is installed."
            fi
        else
            FFMPEG_VER=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
            print_success "ffmpeg found (${FFMPEG_VER})"
        fi

        # Ask about Lighttpd installation for production
        print_info "Lighttpd is recommended for production deployments"
        print_info "It provides better performance than PHP's built-in server"
        read -p "Install Lighttpd + PHP-CGI for production use? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Installing Lighttpd and PHP packages..."
            sudo apt install -y lighttpd php-cgi php-sqlite3 php-curl php-json
            print_success "Lighttpd installed! Use './start-lighttpd.sh' to start it"
        else
            print_info "Skipping Lighttpd installation (you can use './start-php.sh' for development)"
        fi
    fi
}

# Create virtual environment
create_venv() {
    if [ -d "$VENV_NAME" ]; then
        print_warning "Virtual environment '$VENV_NAME' already exists"
        read -p "Remove and recreate? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Removing existing virtual environment..."
            rm -rf "$VENV_NAME"
        else
            print_info "Using existing virtual environment"
            return 0
        fi
    fi

    print_info "Creating virtual environment '$VENV_NAME'..."
    $PYTHON_CMD -m venv "$VENV_NAME"
    print_success "Virtual environment created!"
}

# Activate virtual environment
activate_venv() {
    print_info "Activating virtual environment..."
    source "$VENV_NAME/bin/activate"
    print_success "Virtual environment activated!"

    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip
}

# Install dependencies
install_dependencies() {
    print_info "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
    print_success "Dependencies installed!"

    # Ask about dev dependencies
    read -p "Install development dependencies? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Installing development dependencies..."
        pip install -r requirements-dev.txt
        print_success "Development dependencies installed!"
    fi
}

# ── .env helpers ──────────────────────────────────────────────────────────
#
# These edit .env by targeting one KEY=value line at a time (sed) rather
# than rewriting the whole file, which is exactly the class of bug the PHP
# setup wizard hit repeatedly in practice (a full-file rewrite silently
# mangled unrelated lines/values). A line that isn't touched here is left
# completely alone, comments included.

# Set (or append) one KEY=value line in .env.
_env_set() {
    local key="$1" val="$2"
    local esc
    esc=$(printf '%s' "$val" | sed -e 's/[\&|]/\\&/g')
    if grep -q "^${key}=" .env; then
        sed -i "s|^${key}=.*|${key}=${esc}|" .env
    else
        echo "${key}=${esc}" >> .env
    fi
}

# Prompt for one value, showing a default (used verbatim if Enter is
# pressed) and re-prompting forever if required and left blank.
_prompt_env() {
    local prompt="$1" default="$2" required="$3" varname="$4"
    local input
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " input
        input="${input:-$default}"
    else
        read -p "$prompt: " input
    fi
    if [ "$required" = "required" ]; then
        while [ -z "$input" ]; do
            print_warning "This value is required."
            read -p "$prompt: " input
        done
    fi
    eval "$varname=\"\$input\""
}

# Create .env (from the template, if missing) and interactively fill in the
# handful of settings every install actually needs, with examples.
setup_env() {
    if [ -f ".env" ]; then
        print_success ".env file already exists"
        read -p "Reconfigure the essential settings now? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 0
        fi
        cp .env .env.bak
        print_info "Backed up existing .env to .env.bak first."
    else
        print_info "Creating .env file from template..."
        cp .env.example .env
    fi

    echo ""
    print_info "Let's set the essentials. Press Enter to accept a [default] where shown."
    echo ""

    _prompt_env "Jellyfin URL (e.g. http://192.168.1.50:8096)" "" "required" jellyfin_url
    _prompt_env "Jellyfin API Key — Jellyfin Dashboard -> API Keys (e.g. a81bbacea1f349ec96cc1cc084135f38)" "" "required" jellyfin_api_key

    detected_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    _prompt_env "JellyStream Public URL — the address JELLYFIN uses to reach THIS machine (must NOT be localhost)" "http://${detected_ip:-192.168.1.100}:8000" "" jellystream_public_url

    _prompt_env "Preferred audio language, ISO 639-2 (e.g. eng, fre, spa, jpn)" "eng" "" preferred_audio_language

    print_info "Media path map: only needed if JellyStream and Jellyfin see the SAME media files at DIFFERENT paths (e.g. separate machines with different mount points). Leave blank if they match."
    _prompt_env "Media path map (e.g. /media:/mnt/nas/media)" "" "" media_path_map

    _env_set "JELLYFIN_URL" "$jellyfin_url"
    _env_set "JELLYFIN_API_KEY" "$jellyfin_api_key"
    _env_set "JELLYSTREAM_PUBLIC_URL" "$jellystream_public_url"
    _env_set "PREFERRED_AUDIO_LANGUAGE" "$preferred_audio_language"
    _env_set "MEDIA_PATH_MAP" "$media_path_map"
    # HOST must stay 0.0.0.0 — binding to a specific IP breaks the PHP
    # frontend's own server-side calls to the API. Force it instead of
    # asking; a prior deployment broke exactly this way.
    _env_set "HOST" "0.0.0.0"

    print_success ".env configured!"
    print_info "JELLYFIN_USER_ID and JELLYFIN_DEVICE_ID are left blank on purpose (both auto-detect/auto-generate). If you ever edit .env by hand, don't add a comment after the \"=\" on a line meant to be blank — .env files don't strip inline comments the way shell scripts do, so \"KEY=  # note\" can end up read back as the literal text \"# note\"."
}

# Create necessary directories
create_directories() {
    print_info "Creating data directories..."
    mkdir -p data/database data/commercials data/logos logs
    print_success "Data directories created!"
}

# ── Dedicated service user ──────────────────────────────────────────────────

SERVICE_USER="jellystream"

# Create (or reuse) a system user with no login/home, dedicated to running
# the JellyStream services — rather than whatever interactive user happens
# to run this script. Idempotent: safe to re-run.
create_service_user() {
    print_info "Setting up dedicated service user '$SERVICE_USER'..."
    read -p "Create/configure the '$SERVICE_USER' system user to run JellyStream as? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_info "Skipping — deploy/systemd/*.service default to User=$SERVICE_USER; edit them if you're running as someone else."
        return 0
    fi

    if id "$SERVICE_USER" &>/dev/null; then
        print_success "System user '$SERVICE_USER' already exists"
    else
        print_info "Creating system user '$SERVICE_USER' (no login, no home directory)..."
        sudo useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
        print_success "Created system user '$SERVICE_USER'"
    fi

    # GPU access for hardware-accelerated transcoding (the channel Hardware
    # Acceleration setting). The render device node is normally owned by
    # group 'render' and sometimes also 'video' — only add groups that
    # actually exist on this system (a headless box with no GPU driver
    # installed yet won't have 'render' at all).
    for grp in render video; do
        if getent group "$grp" >/dev/null 2>&1; then
            sudo usermod -aG "$grp" "$SERVICE_USER"
            print_success "Added '$SERVICE_USER' to group '$grp'"
        else
            print_warning "Group '$grp' does not exist on this system — skipping (no GPU driver installed?)"
        fi
    done

    # Let the person running setup read logs/the database without sudo too.
    local current_user
    current_user="$(whoami)"
    if [ "$current_user" != "$SERVICE_USER" ]; then
        sudo usermod -aG "$SERVICE_USER" "$current_user"
        print_info "Added '$current_user' to the '$SERVICE_USER' group so you can read logs/database without sudo."
        print_warning "Log out and back in (or run: newgrp $SERVICE_USER) for that to take effect in this shell."
    fi
}

# Grant the service user read access to the whole project tree, and
# read+write access to the directories it actually needs to write at
# runtime, without changing who OWNS the tree (the admin user who ran this
# script keeps full control — only group permissions change).
configure_permissions() {
    if ! id "$SERVICE_USER" &>/dev/null; then
        print_info "Service user '$SERVICE_USER' not present — skipping permission setup."
        return 0
    fi

    print_info "Setting permissions for '$SERVICE_USER' on $(pwd)..."

    sudo chgrp -R "$SERVICE_USER" .
    sudo chmod -R g+rX .   # capital X: only sets +x on things already executable somewhere (dirs, venv binaries) — never makes plain files executable

    mkdir -p data/database data/commercials data/logos logs
    sudo chgrp -R "$SERVICE_USER" data logs
    sudo chmod -R g+rwX data logs

    # Narrow exceptions: the PHP frontend's own web-based setup wizard
    # (setup.php) saves .env and app/web/php/.phpconfig directly, running
    # as this same service user under lighttpd/PHP-CGI. Grant write on
    # just those two files (not the rest of the tree) so that wizard keeps
    # working, rather than it silently failing with a permission error.
    if [ -f .env ]; then
        sudo chgrp "$SERVICE_USER" .env
        sudo chmod g+rw .env
    fi
    touch app/web/php/.phpconfig 2>/dev/null || true
    if [ -f app/web/php/.phpconfig ]; then
        sudo chgrp "$SERVICE_USER" app/web/php/.phpconfig
        sudo chmod g+rw app/web/php/.phpconfig
    fi

    print_success "Permissions configured for '$SERVICE_USER'"
    print_warning "If your media library lives outside this project directory (the usual case), make sure '$SERVICE_USER' can read it too — e.g. by adding it to whatever group owns those files. JellyStream can't automate that part since it doesn't know your media layout."
}

# Main setup process
main() {
    # Change to script directory
    cd "$(dirname "$0")"

    check_python
    check_system_requirements
    create_venv
    activate_venv
    install_dependencies
    setup_env
    create_directories
    create_service_user
    configure_permissions

    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   Setup completed successfully! 🎉        ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
    echo ""
    print_info "Next steps:"
    echo "  1. Review .env if you want to tweak anything further"
    echo "  2. Run as a systemd service (recommended — see deploy/README.md):"
    echo "     ${YELLOW}sudo cp deploy/systemd/*.service /etc/systemd/system/${NC}"
    echo "     ${YELLOW}sudo systemctl daemon-reload${NC}"
    echo "     ${YELLOW}sudo systemctl enable --now jellystream-api jellystream-web${NC}"
    echo "     (those units already default to User=$SERVICE_USER)"
    echo "  3. Open the web UI at: ${YELLOW}http://localhost:8080${NC}"
    echo "  4. Create channels, build collections, and register with Jellyfin Live TV"
    echo ""

    # Offer a quick foreground test as the CURRENT user — separate from the
    # systemd service, which runs as $SERVICE_USER (see step 2 above).
    read -p "Start JellyStream now for a quick test, as the current user? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Starting JellyStream..."
        echo ""
        $PYTHON_CMD run.py
    else
        print_info "You can start it later with: ${YELLOW}./start.sh${NC} (quick test) or the systemd service (step 2 above)."
    fi
}

# Run main function
main
