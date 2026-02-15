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

        curl_close($ch);

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
     * Get health status
     */
    public function healthCheck() {
        return $this->get('/health');
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
    public function createStream($name, $jellyfin_library_id, $description = null) {
        return $this->post('/streams/', [
            'name' => $name,
            'jellyfin_library_id' => $jellyfin_library_id,
            'description' => $description
        ]);
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
    public function getJellyfinLibraryItems($library_id) {
        return $this->get("/jellyfin/items/{$library_id}");
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
}
