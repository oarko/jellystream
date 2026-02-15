# Setup Guide

## Prerequisites

- Python 3.11 or higher
- Jellyfin server (9.0 or higher recommended)
- Git

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd jellystream
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

For development:
```bash
pip install -r requirements-dev.txt
```

### 4. Configure Environment

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and configure your Jellyfin connection:

```env
JELLYFIN_URL=http://your-jellyfin-server:8096
JELLYFIN_API_KEY=your_api_key_here
```

#### Getting a Jellyfin API Key

1. Log into your Jellyfin server
2. Go to Dashboard → API Keys
3. Click "+" to create a new API key
4. Give it a name (e.g., "JellyStream")
5. Copy the generated key to your `.env` file

### 5. Initialize Database

The database will be automatically created when you first run the application.

### 6. Run the Application

```bash
python run.py
```

Or using uvicorn directly:

```bash
uvicorn app.main:app --reload
```

The application will be available at: http://localhost:8000

## Docker Setup

### Using Docker Compose (Recommended)

1. Configure your `.env` file as described above

2. Build and run:

```bash
docker-compose up -d
```

3. View logs:

```bash
docker-compose logs -f
```

4. Stop the container:

```bash
docker-compose down
```

### Using Docker Directly

1. Build the image:

```bash
docker build -t jellystream .
```

2. Run the container:

```bash
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e JELLYFIN_URL=http://your-jellyfin-server:8096 \
  -e JELLYFIN_API_KEY=your_api_key \
  --name jellystream \
  jellystream
```

## Verification

1. Check the health endpoint:

```bash
curl http://localhost:8000/health
```

2. Visit the API documentation:

```
http://localhost:8000/docs
```

3. Test Jellyfin connection:

```bash
curl http://localhost:8000/api/jellyfin/libraries
```

## Troubleshooting

### Database Issues

If you encounter database issues, try deleting and recreating:

```bash
rm -rf data/database/jellystream.db
python run.py  # Will recreate the database
```

### Jellyfin Connection Issues

- Verify your Jellyfin server is accessible
- Check that the API key is correct
- Ensure there are no firewall issues
- Try accessing Jellyfin URL from the machine running JellyStream

### Port Already in Use

If port 8000 is already in use, change the PORT in your `.env` file:

```env
PORT=8001
```

## Next Steps

- Read the [API Documentation](API.md)
- Configure your first stream
- Set up scheduled programming
- Add commercials and logos
