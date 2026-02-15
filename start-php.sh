#!/bin/bash
# Start PHP development server for JellyStream frontend

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PHP_HOST="localhost"
PHP_DIR="app/web/php"
PHP_CONFIG_FILE="$PHP_DIR/.phpconfig"

# Read port from config file if it exists
if [ -f "$PHP_CONFIG_FILE" ]; then
    PHP_PORT=$(grep "PHP_FRONTEND_PORT" "$PHP_CONFIG_FILE" | cut -d'=' -f2)
    if [ -z "$PHP_PORT" ]; then
        PHP_PORT="8080"
    fi
else
    PHP_PORT="8080"
fi

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   JellyStream PHP Frontend Starter       ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""

# Check if PHP is installed
if ! command -v php &> /dev/null; then
    echo -e "${YELLOW}Error: PHP is not installed!${NC}"
    echo "Please install PHP first:"
    echo "  sudo apt install php php-sqlite3 php-curl php-json"
    exit 1
fi

# Check PHP version
PHP_VERSION=$(php -r 'echo PHP_VERSION;')
echo -e "${GREEN}✓ PHP version: $PHP_VERSION${NC}"

# Check required extensions
echo -e "${BLUE}Checking PHP extensions...${NC}"
MISSING_EXTENSIONS=()

for ext in pdo_sqlite curl json; do
    if ! php -m | grep -q "^$ext$"; then
        MISSING_EXTENSIONS+=($ext)
    else
        echo -e "${GREEN}✓ $ext${NC}"
    fi
done

if [ ${#MISSING_EXTENSIONS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Missing extensions: ${MISSING_EXTENSIONS[*]}${NC}"
    echo "Install with:"
    echo "  sudo apt install php-sqlite3 php-curl php-json"
    exit 1
fi

# Change to PHP directory
echo -e "${GREEN}✓ All required PHP extensions are installed!${NC}"
echo -e "${BLUE}Changing to PHP directory: $PHP_DIR${NC}"
cd "$PHP_DIR"

echo ""
echo -e "${GREEN}Starting PHP development server...${NC}"
echo -e "${BLUE}Frontend URL: http://${PHP_HOST}:${PHP_PORT}${NC}"
echo -e "${BLUE}API Backend: http://localhost:8000${NC}"
echo ""
echo -e "${YELLOW}Make sure the FastAPI backend is running on port 8000!${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Start PHP server
php -S ${PHP_HOST}:${PHP_PORT}
