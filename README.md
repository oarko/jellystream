# JellyStream

A media streaming integration for Jellyfin that allows you to create custom streaming channels with scheduled programming.

## Features

- 📺 Create custom streaming channels from Jellyfin libraries
- ⏰ Schedule media playback with precise timing
- 🎬 Support for commercials and station logos
- 🔄 Automatic content rotation
- 🌐 Web interface for management
- 📡 RESTful API for automation

## Quick Start

### Prerequisites

- Python 3.11+
- Jellyfin server with API access

### Automated Installation (Recommended)

The easiest way to get started, especially on Debian/Ubuntu systems:

```bash
./setup.sh
```

This script will:
- ✅ Detect your OS and install required packages (python3-venv on Debian/Ubuntu)
- ✅ Create a virtual environment
- ✅ Install all dependencies
- ✅ Set up configuration files
- ✅ Optionally start the application

After setup, run JellyStream with:
```bash
./start.sh
```

### Manual Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd jellystream
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your Jellyfin URL and API key
```

5. Run the application:
```bash
python run.py
```

For detailed installation instructions and troubleshooting, see [INSTALL.md](INSTALL.md).

## Development

### Setup Development Environment

```bash
pip install -r requirements-dev.txt
```

### Run Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black app/

# Check style
flake8 app/

# Type checking
mypy app/
```

## API Documentation

Once running, access the interactive API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Configuration

All configuration is done through environment variables. See `.env.example` for available options.

## Project Structure

```
jellystream/
├── app/
│   ├── api/              # API endpoints
│   ├── core/             # Core functionality
│   ├── integrations/     # External service integrations
│   ├── models/           # Database models
│   ├── utils/            # Utility functions
│   └── web/              # Web interface
├── config/               # Configuration files
├── data/                 # Data storage
│   ├── commercials/      # Commercial videos
│   ├── database/         # SQLite database
│   └── logos/            # Channel logos
├── docker/               # Docker configuration
├── docs/                 # Documentation
└── tests/                # Tests

```

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
