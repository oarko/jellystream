#!/bin/bash
# Start Lighttpd for JellyStream (production-ready local server)

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   JellyStream Lighttpd Starter            ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""

# Configuration
PHP_CONFIG_FILE="app/web/php/.phpconfig"
LIGHTTPD_CONFIG="lighttpd.conf"
LIGHTTPD_PID_FILE="/tmp/jellystream-lighttpd.pid"

# Read port from config file if it exists
if [ -f "$PHP_CONFIG_FILE" ]; then
    PHP_PORT=$(grep "PHP_FRONTEND_PORT" "$PHP_CONFIG_FILE" | cut -d'=' -f2)
    API_PORT=$(grep "API_BACKEND_PORT" "$PHP_CONFIG_FILE" | cut -d'=' -f2)
    if [ -z "$PHP_PORT" ]; then
        PHP_PORT="8080"
    fi
    if [ -z "$API_PORT" ]; then
        API_PORT="8000"
    fi
else
    PHP_PORT="8080"
    API_PORT="8000"
fi

# Check if Lighttpd is installed
if ! command -v lighttpd &> /dev/null; then
    echo -e "${RED}Error: Lighttpd is not installed!${NC}"
    echo ""
    echo "Install Lighttpd:"
    echo -e "${YELLOW}  Debian/Ubuntu:${NC}"
    echo "    sudo apt install lighttpd php-cgi php-sqlite3 php-curl php-json"
    echo ""
    echo -e "${YELLOW}  Fedora/RHEL:${NC}"
    echo "    sudo dnf install lighttpd php-cgi php-pdo php-json"
    echo ""
    echo -e "${YELLOW}  Arch Linux:${NC}"
    echo "    sudo pacman -S lighttpd php-cgi"
    echo ""
    exit 1
fi

# Check PHP-CGI
if ! command -v php-cgi &> /dev/null; then
    echo -e "${RED}Error: PHP-CGI is not installed!${NC}"
    echo "Install with: sudo apt install php-cgi"
    exit 1
fi

# Get PHP-CGI path
PHP_CGI=$(which php-cgi)

# Create Lighttpd config
cat > "$LIGHTTPD_CONFIG" <<EOF
# JellyStream Lighttpd Configuration
# Auto-generated - do not edit manually

server.modules = (
    "mod_access",
    "mod_fastcgi",
    "mod_accesslog"
)

server.document-root = "$(pwd)/app/web/php"
server.upload-dirs = ( "/tmp" )
server.errorlog = "$(pwd)/logs/lighttpd-error.log"
server.pid-file = "$LIGHTTPD_PID_FILE"
server.port = $PHP_PORT

server.bind = "0.0.0.0"

# Index files
index-file.names = ( "index.php", "index.html" )

# MIME types
mimetype.assign = (
    ".html" => "text/html",
    ".txt" => "text/plain",
    ".jpg" => "image/jpeg",
    ".png" => "image/png",
    ".css" => "text/css",
    ".js" => "application/javascript",
    ".json" => "application/json"
)

# Access log
accesslog.filename = "$(pwd)/logs/lighttpd-access.log"

# FastCGI for PHP
fastcgi.server = ( ".php" =>
    ((
        "bin-path" => "$PHP_CGI",
        "socket" => "/tmp/jellystream-php.socket",
        "max-procs" => 2,
        "bin-environment" => (
            "PHP_FCGI_CHILDREN" => "4",
            "PHP_FCGI_MAX_REQUESTS" => "1000"
        ),
        "broken-scriptfilename" => "enable"
    ))
)

# Deny access to hidden files
\$HTTP["url"] =~ "^/\." {
    url.access-deny = ( "" )
}

# Deny access to config files
\$HTTP["url"] =~ "\.(env|phpconfig)" {
    url.access-deny = ( "" )
}
EOF

# Create logs directory
mkdir -p logs

# Check if already running
if [ -f "$LIGHTTPD_PID_FILE" ]; then
    OLD_PID=$(cat "$LIGHTTPD_PID_FILE")
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}Lighttpd is already running (PID: $OLD_PID)${NC}"
        echo "Stop it with: sudo kill $OLD_PID"
        exit 1
    else
        # Stale PID file
        rm -f "$LIGHTTPD_PID_FILE"
    fi
fi

echo -e "${GREEN}✓ Configuration created${NC}"
echo -e "${GREEN}✓ PHP-CGI found: $PHP_CGI${NC}"
echo ""
echo -e "${BLUE}Starting Lighttpd...${NC}"
echo -e "${BLUE}Frontend URL: http://$(hostname -I | awk '{print $1}'):${PHP_PORT}${NC}"
echo -e "${BLUE}API Backend: http://localhost:${API_PORT}${NC}"
echo ""
echo -e "${YELLOW}Make sure the FastAPI backend is running on port ${API_PORT}!${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Start Lighttpd (requires sudo for ports < 1024)
if [ "$PHP_PORT" -lt 1024 ]; then
    echo -e "${YELLOW}Port $PHP_PORT requires sudo${NC}"
    sudo lighttpd -D -f "$LIGHTTPD_CONFIG"
else
    lighttpd -D -f "$LIGHTTPD_CONFIG"
fi
