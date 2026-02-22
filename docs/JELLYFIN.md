# Jellyfin Integration Guide

## Authentication

JellyStream uses proper Jellyfin authentication with all required headers:

- **Authorization**: MediaBrowser token with client information
- **Client**: Application name (default: "JellyStream")
- **Device**: Device name (default: "JellyStream Server")
- **DeviceId**: Unique device identifier (auto-generated)
- **Version**: Application version

## Configuration

Add these settings to your `.env` file:

```env
# Required
JELLYFIN_URL=http://localhost:8096
JELLYFIN_API_KEY=your_api_key_here

# Optional (uses defaults if not specified)
JELLYFIN_CLIENT_NAME=JellyStream
JELLYFIN_DEVICE_NAME=JellyStream Server
JELLYFIN_DEVICE_ID=  # Auto-generated UUID if empty
```

## Getting a Jellyfin API Key

1. Open your Jellyfin web interface
2. Go to **Dashboard** → **API Keys**
3. Click the **+** button to create a new key
4. Enter a name (e.g., "JellyStream")
5. Copy the generated key to your `.env` file

## Testing the Connection

### Using curl

Test the connection directly:

```bash
curl -X GET "http://localhost:8000/api/jellyfin/libraries"
```

### Using the API Docs

1. Start JellyStream: `python run.py`
2. Open http://localhost:8000/docs
3. Navigate to the **jellyfin** section
4. Try the `/api/jellyfin/libraries` endpoint

## API Endpoints

### Get Libraries

**GET** `/api/jellyfin/libraries`

Returns all available Jellyfin libraries.

**Example Response:**
```json
{
  "libraries": [
    {
      "Name": "Movies",
      "CollectionType": "movies",
      "ItemId": "abc123..."
    },
    {
      "Name": "TV Shows",
      "CollectionType": "tvshows",
      "ItemId": "def456..."
    }
  ]
}
```

### Get Genres for a Library

**GET** `/api/jellyfin/genres/{library_id}`

Returns all genres present in a library. Used when configuring genre filters for a channel.

**Parameters:**
- `library_id`: The library ID (`ItemId`) from the libraries endpoint

**Example Response:**
```json
{
  "genres": ["Action", "Comedy", "Crime", "Drama", "Horror", "Sci-Fi", "Thriller"]
}
```

### Get Library Items

**GET** `/api/jellyfin/items/{parent_id}`

Returns items from a library or parent item (series, season, etc.).

**Parameters:**
- `parent_id`: The ID of the parent item (library `ItemId`, series ID, or season ID)

**Example Response:**
```json
{
  "items": [
    {
      "Name": "The Matrix",
      "Id": "item123",
      "Type": "Movie",
      "RunTimeTicks": 81630000000
    }
  ]
}
```

## Authentication Headers

The JellyfinClient automatically constructs the proper authentication header:

```python
Authorization: MediaBrowser Token="your_api_key", Client="JellyStream", Device="JellyStream Server", DeviceId="unique-uuid", Version="0.1.0"
```

This matches Jellyfin's authentication requirements as documented in their API specification.

## Troubleshooting

### 401 Unauthorized

- Verify your API key is correct
- Check that the API key hasn't been revoked in Jellyfin
- Ensure your Jellyfin server is accessible

### 400 Bad Request

- Verify all required authentication headers are present
- Check that JELLYFIN_URL doesn't have a trailing slash
- Ensure JELLYFIN_URL includes the protocol (http:// or https://)

### Connection Refused

- Verify Jellyfin is running
- Check the JELLYFIN_URL is correct
- Ensure there are no firewall rules blocking the connection

### SSL Certificate Errors

If using HTTPS with a self-signed certificate, you may need to:
1. Use a proper SSL certificate, or
2. Configure aiohttp to skip SSL verification (not recommended for production)

## Advanced Usage

### Custom Client Information

You can customize the client information in your `.env`:

```env
JELLYFIN_CLIENT_NAME=MyCustomApp
JELLYFIN_DEVICE_NAME=Production Server
JELLYFIN_DEVICE_ID=my-fixed-device-id
```

### Using the JellyfinClient Directly

```python
from app.integrations.jellyfin import JellyfinClient
from app.core.config import settings

client = JellyfinClient(
    base_url=settings.JELLYFIN_URL,
    api_key=settings.JELLYFIN_API_KEY,
    client_name="MyApp",
    device_name="Custom Device",
    device_id="custom-id-123",
    version="1.0.0"
)

# Get libraries
libraries = await client.get_libraries()

# Get items from a library
items = await client.get_library_items("library-id-here")

# Get specific item info
item = await client.get_item_info("item-id-here")

# Get stream URL
stream_url = await client.get_stream_url("item-id-here")
```

## References

- [Jellyfin API Documentation](https://api.jellyfin.org/)
- [Jellyfin Authentication](https://jellyfin.org/docs/general/networking/authentication.html)
