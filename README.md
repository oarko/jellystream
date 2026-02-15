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

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd jellystream
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your Jellyfin URL and API key
```

4. Run the application:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

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
