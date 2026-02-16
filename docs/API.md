# JellyStream API Documentation

## Base URL

```
http://localhost:8000
```

## API Routing Structure

The API uses a prefix-based routing system:
- Main application routes: `/api/*`
- Router prefixes combine with the main prefix
- Example: streams router with prefix `/streams` → `/api/streams/`

All API endpoints below assume the `/api` prefix is already included.

## Authentication

Currently, the API does not require authentication. This may change in future versions.

## Endpoints

### Health Check

**GET** `/health`

Returns the health status of the application.

**Response:**
```json
{
  "status": "healthy"
}
```

---

### Streams

Streams represent virtual TV channels that combine Jellyfin media content with scheduling.

#### Get All Streams

**GET** `/api/streams/`

Returns a list of all configured streams.

**Response:**
```json
[
  {
    "id": 1,
    "name": "Classic Movies",
    "description": "24/7 classic movie channel",
    "jellyfin_library_id": "abc123",
    "stream_url": "http://localhost:8000/api/livetv/stream/1",
    "enabled": true,
    "tuner_host_id": "tuner-abc123",
    "listing_provider_id": "provider-xyz789",
    "channel_number": "100.1",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

#### Get Stream by ID

**GET** `/api/streams/{stream_id}`

Returns details for a specific stream.

**Parameters:**
- `stream_id` (path): Stream ID

**Response:**
```json
{
  "id": 1,
  "name": "Classic Movies",
  "description": "24/7 classic movie channel",
  "jellyfin_library_id": "abc123",
  "stream_url": "http://localhost:8000/api/livetv/stream/1",
  "enabled": true,
  "tuner_host_id": "tuner-abc123",
  "listing_provider_id": "provider-xyz789",
  "channel_number": "100.1",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

#### Create Stream

**POST** `/api/streams/`

Creates a new stream.

**Request Parameters:**
- `name` (required): Stream name
- `jellyfin_library_id` (required): Jellyfin library ID
- `description` (optional): Stream description
- `channel_number` (optional): Virtual channel number (e.g., "100.1")

**Response:**
```json
{
  "id": 1,
  "message": "Stream created successfully"
}
```

#### Update Stream

**PUT** `/api/streams/{stream_id}`

Updates an existing stream.

**Parameters:**
- `stream_id` (path): Stream ID
- `name` (optional): New stream name
- `jellyfin_library_id` (optional): New Jellyfin library ID
- `description` (optional): New description
- `enabled` (optional): Enable/disable stream
- `channel_number` (optional): Virtual channel number
- `tuner_host_id` (optional): Jellyfin TunerHost ID
- `listing_provider_id` (optional): Jellyfin ListingProvider ID

**Response:**
```json
{
  "id": 1,
  "message": "Stream updated successfully"
}
```

#### Delete Stream

**DELETE** `/api/streams/{stream_id}`

Deletes a stream.

**Parameters:**
- `stream_id` (path): Stream ID

**Response:**
```json
{
  "message": "Stream deleted successfully"
}
```

---

### Schedules

Schedules define what media content plays on a stream at specific times.

#### Get All Schedules

**GET** `/api/schedules/`

Returns all scheduled items across all streams.

**Response:**
```json
[
  {
    "id": 1,
    "stream_id": 1,
    "title": "The Godfather",
    "media_item_id": "xyz789",
    "scheduled_time": "2024-01-01T20:00:00",
    "duration": 10500,
    "extra_metadata": "{\"type\":\"Movie\",\"year\":1972}",
    "created_at": "2024-01-01T00:00:00"
  }
]
```

#### Get Schedule by ID

**GET** `/api/schedules/{schedule_id}`

Returns details for a specific schedule.

**Parameters:**
- `schedule_id` (path): Schedule ID

**Response:**
```json
{
  "id": 1,
  "stream_id": 1,
  "title": "The Godfather",
  "media_item_id": "xyz789",
  "scheduled_time": "2024-01-01T20:00:00",
  "duration": 10500,
  "extra_metadata": "{\"type\":\"Movie\",\"year\":1972}",
  "created_at": "2024-01-01T00:00:00"
}
```

#### Get Schedules for Stream

**GET** `/api/schedules/stream/{stream_id}`

Returns all schedules for a specific stream, ordered by scheduled time.

**Parameters:**
- `stream_id` (path): Stream ID

**Response:**
```json
[
  {
    "id": 1,
    "stream_id": 1,
    "title": "The Godfather",
    "media_item_id": "xyz789",
    "scheduled_time": "2024-01-01T20:00:00",
    "duration": 10500,
    "extra_metadata": "{\"type\":\"Movie\",\"year\":1972}",
    "created_at": "2024-01-01T00:00:00"
  }
]
```

#### Create Schedule

**POST** `/api/schedules/`

Creates a new schedule entry.

**Request Parameters:**
- `stream_id` (required): Stream ID
- `title` (required): Schedule title/name
- `media_item_id` (required): Jellyfin media item ID
- `scheduled_time` (required): ISO 8601 datetime string
- `duration` (required): Duration in seconds
- `metadata` (optional): JSON string with extra metadata

**Response:**
```json
{
  "id": 1,
  "message": "Schedule created successfully"
}
```

#### Update Schedule

**PUT** `/api/schedules/{schedule_id}`

Updates an existing schedule entry.

**Parameters:**
- `schedule_id` (path): Schedule ID
- `title` (optional): New title
- `media_item_id` (optional): New media item ID
- `scheduled_time` (optional): New scheduled time (ISO 8601)
- `duration` (optional): New duration in seconds
- `metadata` (optional): New metadata JSON string

**Response:**
```json
{
  "id": 1,
  "message": "Schedule updated successfully"
}
```

#### Delete Schedule

**DELETE** `/api/schedules/{schedule_id}`

Deletes a schedule entry.

**Parameters:**
- `schedule_id` (path): Schedule ID

**Response:**
```json
{
  "message": "Schedule deleted successfully"
}
```

---

### Jellyfin Integration

Integration with Jellyfin media server for browsing libraries and retrieving media content.

#### Get Current User

**GET** `/api/jellyfin/users`

Returns the current Jellyfin user information. Used for auto-detecting user ID.

**Response:**
```json
{
  "user": {
    "Id": "user123",
    "Name": "JellyStream User",
    "ServerId": "server456"
  }
}
```

#### Get Libraries

**GET** `/api/jellyfin/libraries`

Returns all available Jellyfin libraries (views) for the configured user.

**Response:**
```json
{
  "libraries": [
    {
      "Id": "abc123",
      "Name": "Movies",
      "CollectionType": "movies"
    },
    {
      "Id": "def456",
      "Name": "TV Shows",
      "CollectionType": "tvshows"
    }
  ]
}
```

#### Get Library Items

**GET** `/api/jellyfin/items/{parent_id}`

Returns items from a specific Jellyfin library or container with pagination and sorting support.

**Parameters:**
- `parent_id` (path): Parent library or container ID
- `recursive` (query, optional): If true, returns all descendants. Default: false (single level)
- `limit` (query, optional): Number of items per page. Default: 50
- `start_index` (query, optional): Starting index for pagination. Default: 0
- `sort_by` (query, optional): Sort field. Default: "SortName"
  - Available options: SortName, PremiereDate, DateCreated, CommunityRating, Runtime, PlayCount, Random, and more
- `sort_order` (query, optional): Sort direction. Options: Ascending, Descending. Default: "Ascending"
- `include_item_types` (query, optional): Filter by item types (comma-separated). Example: "Series,Season,Episode"

**Example Request:**
```
GET /api/jellyfin/items/abc123?recursive=false&limit=50&start_index=0&sort_by=SortName&sort_order=Ascending
```

**Response:**
```json
{
  "Items": [
    {
      "Id": "xyz789",
      "Name": "The Godfather",
      "Type": "Movie",
      "RunTimeTicks": 105000000000,
      "PremiereDate": "1972-03-24",
      "CommunityRating": 9.2
    },
    {
      "Id": "series123",
      "Name": "Breaking Bad",
      "Type": "Series",
      "ChildCount": 5
    }
  ],
  "TotalRecordCount": 150,
  "StartIndex": 0
}
```

**Hierarchical Navigation (TV Shows):**

For `CollectionType: "tvshows"` libraries, navigate hierarchically:
1. Library → Series (recursive=false)
2. Series → Seasons (use Series ID as parent_id, recursive=false)
3. Season → Episodes (use Season ID as parent_id, recursive=false)

---

### Live TV Integration

JellyStream integrates with Jellyfin's Live TV system by generating M3U playlists and XMLTV EPG data.

#### Get Stream M3U Playlist

**GET** `/api/livetv/m3u/{stream_id}`

Generates an M3U playlist for a specific stream.

**Parameters:**
- `stream_id` (path): Stream ID

**Response (Content-Type: application/x-mpegURL):**
```m3u
#EXTM3U
#EXTINF:-1 channel-id="1" channel-number="100.1" tvg-name="Classic Movies" tvg-id="1" group-title="JellyStream",100.1 Classic Movies
http://localhost:8000/api/livetv/stream/1
```

#### Get All Streams M3U Playlist

**GET** `/api/livetv/m3u/all`

Generates an M3U playlist containing all enabled streams.

**Response (Content-Type: application/x-mpegURL):**
```m3u
#EXTM3U
#EXTINF:-1 channel-id="1" channel-number="100.1" tvg-name="Classic Movies" tvg-id="1" group-title="JellyStream",100.1 Classic Movies
http://localhost:8000/api/livetv/stream/1
#EXTINF:-1 channel-id="2" channel-number="100.2" tvg-name="TV Marathon" tvg-id="2" group-title="JellyStream",100.2 TV Marathon
http://localhost:8000/api/livetv/stream/2
```

#### Get Stream XMLTV EPG

**GET** `/api/livetv/xmltv/{stream_id}`

Generates XMLTV Electronic Program Guide data for a specific stream.

**Parameters:**
- `stream_id` (path): Stream ID

**Response (Content-Type: application/xml):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE tv SYSTEM "xmltv.dtd">
<tv generator-info-name="JellyStream">
  <channel id="1">
    <display-name>Classic Movies</display-name>
  </channel>
  <programme channel="1" start="20240101200000 +0000" stop="20240101225500 +0000">
    <title>The Godfather</title>
    <category>Movie</category>
  </programme>
</tv>
```

#### Get All Streams XMLTV EPG

**GET** `/api/livetv/xmltv/all`

Generates XMLTV EPG data for all enabled streams.

**Response (Content-Type: application/xml):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE tv SYSTEM "xmltv.dtd">
<tv generator-info-name="JellyStream">
  <channel id="1">
    <display-name>Classic Movies</display-name>
  </channel>
  <channel id="2">
    <display-name>TV Marathon</display-name>
  </channel>
  <programme channel="1" start="20240101200000 +0000" stop="20240101225500 +0000">
    <title>The Godfather</title>
    <category>Movie</category>
  </programme>
  <programme channel="2" start="20240101200000 +0000" stop="20240101203000 +0000">
    <title>Breaking Bad - Pilot</title>
    <sub-title>Breaking Bad</sub-title>
    <category>Episode</category>
  </programme>
</tv>
```

#### Stream Live Content

**GET** `/api/livetv/stream/{stream_id}`

Streams live content based on the current schedule. This endpoint:
1. Checks the current time
2. Finds what media should be playing now
3. Redirects to the actual Jellyfin stream URL

**Parameters:**
- `stream_id` (path): Stream ID

**Response:**
- **302 Redirect** to Jellyfin stream URL
- **404 Not Found** if no content is scheduled at the current time

**Example Usage:**

This endpoint is typically consumed by M3U playlists and is used as the stream URL in Jellyfin's TunerHost configuration.

---

## Integration with Jellyfin Live TV

To register JellyStream as a Live TV source in Jellyfin:

### Step 1: Add TunerHost

**POST** to Jellyfin: `/LiveTv/TunerHosts`

```json
{
  "Type": "m3utuner",
  "Url": "http://localhost:8000/api/livetv/m3u/all",
  "UserAgent": "JellyStream",
  "FriendlyName": "JellyStream Virtual Tuner",
  "ImportFavoritesOnly": false,
  "AllowHWTranscoding": true,
  "EnableStreamLooping": false,
  "Source": "Other",
  "TunerCount": 10,
  "DeviceId": "jellystream-tuner"
}
```

### Step 2: Add ListingProvider

**POST** to Jellyfin: `/LiveTv/ListingProviders`

```json
{
  "Type": "xmltv",
  "Path": "http://localhost:8000/api/livetv/xmltv/all",
  "ListingsId": "jellystream-epg"
}
```

After registration, the `tuner_host_id` and `listing_provider_id` should be stored in the stream record for future reference.

---

## Error Responses

All endpoints may return the following error responses:

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error message"
}
```

---

## Data Formats

### DateTime Format

All datetime fields use ISO 8601 format:
```
2024-01-01T20:00:00
```

### Duration

Duration is specified in seconds (integer):
```
10500  # 2 hours, 55 minutes
```

### Metadata

The `extra_metadata` field stores JSON as a string:
```json
{
  "type": "Movie",
  "year": 1972,
  "seriesName": "Breaking Bad",
  "seasonNumber": 1,
  "episodeNumber": 1
}
```
