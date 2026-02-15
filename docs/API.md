# JellyStream API Documentation

## Base URL

```
http://localhost:8000
```

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
    "stream_url": "http://localhost:8000/stream/1",
    "enabled": true,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

#### Get Stream by ID

**GET** `/api/streams/{stream_id}`

Returns details for a specific stream.

**Response:**
```json
{
  "id": 1,
  "name": "Classic Movies",
  "description": "24/7 classic movie channel",
  "jellyfin_library_id": "abc123",
  "stream_url": "http://localhost:8000/stream/1",
  "enabled": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

#### Create Stream

**POST** `/api/streams/`

Creates a new stream.

**Request Body:**
```json
{
  "name": "Classic Movies",
  "description": "24/7 classic movie channel",
  "jellyfin_library_id": "abc123"
}
```

**Response:**
```json
{
  "id": 1,
  "message": "Stream created successfully"
}
```

#### Delete Stream

**DELETE** `/api/streams/{stream_id}`

Deletes a stream.

**Response:**
```json
{
  "message": "Stream deleted successfully"
}
```

---

### Schedules

#### Get All Schedules

**GET** `/api/schedules/`

Returns all scheduled items.

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
    "metadata": "{}",
    "created_at": "2024-01-01T00:00:00"
  }
]
```

#### Get Schedule by ID

**GET** `/api/schedules/{schedule_id}`

Returns details for a specific schedule.

---

### Jellyfin Integration

#### Get Libraries

**GET** `/api/jellyfin/libraries`

Returns all available Jellyfin libraries.

**Response:**
```json
{
  "libraries": [
    {
      "Id": "abc123",
      "Name": "Movies"
    }
  ]
}
```

#### Get Library Items

**GET** `/api/jellyfin/items/{library_id}`

Returns items from a specific Jellyfin library.

**Response:**
```json
{
  "items": [
    {
      "Id": "xyz789",
      "Name": "The Godfather",
      "Type": "Movie"
    }
  ]
}
```

## Error Responses

All endpoints may return the following error responses:

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error message"
}
```
