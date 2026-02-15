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

# Create .env file if it doesn't exist
setup_env() {
    if [ ! -f ".env" ]; then
        print_info "Creating .env file from template..."
        cp .env.example .env
        print_success ".env file created!"
        print_warning "Please edit .env and configure your Jellyfin settings:"
        echo "  - JELLYFIN_URL"
        echo "  - JELLYFIN_API_KEY"
    else
        print_success ".env file already exists"
    fi
}

# Create necessary directories
create_directories() {
    print_info "Creating data directories..."
    mkdir -p data/database data/commercials data/logos
    print_success "Data directories created!"
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

    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   Setup completed successfully! 🎉        ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
    echo ""
    print_info "Next steps:"
    echo "  1. Edit .env file with your Jellyfin settings"
    echo "  2. Activate the virtual environment:"
    echo "     ${YELLOW}source venv/bin/activate${NC}"
    echo "  3. Start the backend:"
    echo "     ${YELLOW}python run.py${NC}"
    echo "  4. Start the frontend (choose one):"
    echo "     ${YELLOW}./start-php.sh${NC}      (Development - PHP built-in server)"
    echo "     ${YELLOW}./start-lighttpd.sh${NC} (Production - Lighttpd server)"
    echo ""

    # Ask if user wants to run the app now
    read -p "Start JellyStream now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Starting JellyStream..."
        echo ""
        python run.py
    else
        print_info "You can start JellyStream later with: ${YELLOW}python run.py${NC}"
    fi
}

# Run main function
main
