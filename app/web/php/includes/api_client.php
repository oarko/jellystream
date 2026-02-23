<?php
/**
 * JellyStream API Client
 * Handles communication with FastAPI backend
 */

class ApiClient {
    private $base_url;
    private $timeout;

    public function __construct($base_url = API_BASE_URL, $timeout = API_TIMEOUT) {
        $this->base_url = rtrim($base_url, '/');
        $this->timeout = $timeout;
    }

    /**
     * Make GET request to API
     */
    public function get($endpoint, $params = []) {
        $url = $this->base_url . '/' . ltrim($endpoint, '/');

        if (!empty($params)) {
            $url .= '?' . http_build_query($params);
        }

        return $this->request('GET', $url);
    }

    /**
     * Make POST request to API
     */
    public function post($endpoint, $data = []) {
        $url = $this->base_url . '/' . ltrim($endpoint, '/');
        return $this->request('POST', $url, $data);
    }

    /**
     * Make PUT request to API
     */
    public function put($endpoint, $data = []) {
        $url = $this->base_url . '/' . ltrim($endpoint, '/');
        return $this->request('PUT', $url, $data);
    }

    /**
     * Make DELETE request to API
     */
    public function delete($endpoint) {
        $url = $this->base_url . '/' . ltrim($endpoint, '/');
        return $this->request('DELETE', $url);
    }

    /**
     * Execute HTTP request
     */
    private function request($method, $url, $data = null) {
        $ch = curl_init();

        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, $this->timeout);
        curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);

        $headers = ['Content-Type: application/json'];

        if ($data !== null) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
        }

        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);

        $response = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);

        #curl_close($ch);  //deprecated in PHP 8.3, will be closed automatically at the end of the request

        if ($error) {
            return [
                'success' => false,
                'error' => $error,
                'http_code' => $http_code
            ];
        }

        return [
            'success' => ($http_code >= 200 && $http_code < 300),
            'data' => json_decode($response, true),
            'http_code' => $http_code
        ];
    }

    /**
     * Get health status.
     * Health endpoint lives at the application root (/health), not under /api.
     */
    public function healthCheck() {
        $root = preg_replace('#/api/?$#', '', rtrim($this->base_url, '/'));
        return $this->request('GET', $root . '/health');
    }

    /**
     * Get all streams
     */
    public function getStreams() {
        return $this->get('/streams/');
    }

    /**
     * Get specific stream
     */
    public function getStream($id) {
        return $this->get("/streams/{$id}");
    }

    /**
     * Create new stream
     */
    public function createStream($name, $jellyfin_library_id, $description = null, $channel_number = null) {
        $data = [
            'name' => $name,
            'jellyfin_library_id' => $jellyfin_library_id,
            'description' => $description
        ];

        if ($channel_number !== null) {
            $data['channel_number'] = $channel_number;
        }

        return $this->post('/streams/', $data);
    }

    /**
     * Update stream
     */
    public function updateStream($id, $data) {
        return $this->put("/streams/{$id}", $data);
    }

    /**
     * Delete stream
     */
    public function deleteStream($id) {
        return $this->delete("/streams/{$id}");
    }

    /**
     * Get Jellyfin libraries
     */
    public function getJellyfinLibraries() {
        return $this->get('/jellyfin/libraries');
    }

    /**
     * Get items from Jellyfin library
     */
    public function getJellyfinLibraryItems($parent_id, $params = []) {
        // Support pagination, sorting, recursive, and filtering
        return $this->get("/jellyfin/items/{$parent_id}", $params);
    }

    /**
     * Get Jellyfin users
     */
    public function getJellyfinUsers() {
        return $this->get('/jellyfin/users');
    }

    /**
     * Get all schedules
     */
    public function getSchedules() {
        return $this->get('/schedules/');
    }

    /**
     * Get schedules for a specific stream
     */
    public function getStreamSchedules($stream_id) {
        return $this->get("/schedules/stream/{$stream_id}");
    }

    /**
     * Get specific schedule
     */
    public function getSchedule($id) {
        return $this->get("/schedules/{$id}");
    }

    /**
     * Create new schedule
     */
    public function createSchedule($stream_id, $title, $media_item_id, $scheduled_time, $duration, $metadata = null) {
        return $this->post('/schedules/', [
            'stream_id' => $stream_id,
            'title' => $title,
            'media_item_id' => $media_item_id,
            'scheduled_time' => $scheduled_time,
            'duration' => $duration,
            'metadata' => $metadata
        ]);
    }

    /**
     * Update schedule
     */
    public function updateSchedule($id, $data) {
        return $this->put("/schedules/{$id}", $data);
    }

    /**
     * Delete schedule
     */
    public function deleteSchedule($id) {
        return $this->delete("/schedules/{$id}");
    }

    // ── Channel methods (new architecture) ────────────────────────────────────

    /**
     * Get all channels
     */
    public function getChannels() {
        return $this->get('/channels/');
    }

    /**
     * Get a specific channel (includes libraries and genre_filters)
     */
    public function getChannel($id) {
        return $this->get("/channels/{$id}");
    }

    /**
     * Create a new channel.
     *
     * $data must match CreateChannelRequest:
     *   name, description?, channel_number?, schedule_type?,
     *   libraries: [{library_id, library_name, collection_type}],
     *   genre_filters?: [{genre, content_type}]
     */
    public function createChannel($data) {
        return $this->post('/channels/', $data);
    }

    /**
     * Update an existing channel.
     *
     * $data matches UpdateChannelRequest (all fields optional).
     */
    public function updateChannel($id, $data) {
        return $this->put("/channels/{$id}", $data);
    }

    /**
     * Delete a channel (cascades to libraries, genre_filters, schedule_entries)
     */
    public function deleteChannel($id) {
        return $this->delete("/channels/{$id}");
    }

    /**
     * Get schedule entries for a channel within a time window.
     * $params may include: hours_back, hours_forward
     */
    public function getChannelSchedule($channel_id, $params = []) {
        return $this->get("/schedules/channel/{$channel_id}", $params);
    }

    /**
     * Get what is currently playing on a channel.
     */
    public function getNowPlaying($channel_id) {
        return $this->get("/schedules/channel/{$channel_id}/now");
    }

    /**
     * Manually trigger schedule generation for a channel.
     */
    public function generateChannelSchedule($channel_id, $days = 7) {
        return $this->post("/channels/{$channel_id}/generate-schedule?days={$days}");
    }
}
