<?php
/**
 * Port configuration for JellyStream
 * Separate from .env to allow PHP-specific settings
 */

// Try to read from environment first, then fall back to defaults
$php_config_file = __DIR__ . '/../.phpconfig';

// Default ports
$DEFAULT_PHP_PORT = 8080;
$DEFAULT_API_PORT = 8000;

// Read PHP-specific config if it exists
if (file_exists($php_config_file)) {
    $config = parse_ini_file($php_config_file);
    define('PHP_FRONTEND_PORT', $config['PHP_FRONTEND_PORT'] ?? $DEFAULT_PHP_PORT);
    define('API_BACKEND_PORT', $config['API_BACKEND_PORT'] ?? $DEFAULT_API_PORT);
    define('API_HOST', $config['API_HOST'] ?? 'localhost');
} else {
    // Use defaults
    define('PHP_FRONTEND_PORT', $DEFAULT_PHP_PORT);
    define('API_BACKEND_PORT', $DEFAULT_API_PORT);
    define('API_HOST', 'localhost');
}

/**
 * Get the full API URL for server-side PHP calls (api_client.php).
 * Host resolved from: JELLYSTREAM_API_HOST env var → .phpconfig API_HOST → localhost
 */
function getApiBaseUrl() {
    $host = getenv('JELLYSTREAM_API_HOST') ?: API_HOST;
    return 'http://' . $host . ':' . API_BACKEND_PORT . '/api';
}

/**
 * Get the API URL as the browser should call it (for embedding in JavaScript).
 *
 * Uses the same hostname/IP the browser used to reach this PHP page, so
 * the URL resolves correctly even when accessed from a remote machine.
 * Falls back to JELLYSTREAM_API_HOST env var or .phpconfig API_HOST when set.
 */
function getClientApiBaseUrl() {
    // Explicit override (e.g. for reverse-proxy setups)
    $env_host = getenv('JELLYSTREAM_API_HOST');
    if ($env_host && $env_host !== 'localhost' && $env_host !== '127.0.0.1') {
        return 'http://' . $env_host . ':' . API_BACKEND_PORT . '/api';
    }
    // Use the host portion of the browser's request URL
    $http_host = $_SERVER['HTTP_HOST'] ?? 'localhost';
    $host = strtok($http_host, ':'); // strip port if present
    return 'http://' . $host . ':' . API_BACKEND_PORT . '/api';
}

/**
 * Save port configuration
 */
function savePortConfig($php_port, $api_port, $api_host = 'localhost') {
    $php_config_file = __DIR__ . '/../.phpconfig';
    $config = [
        'PHP_FRONTEND_PORT' => $php_port,
        'API_BACKEND_PORT'  => $api_port,
        'API_HOST'          => $api_host,
    ];

    $content = "; JellyStream PHP Configuration\n";
    $content .= "; Auto-generated - do not edit manually\n\n";
    foreach ($config as $key => $value) {
        $content .= "$key=$value\n";
    }

    return file_put_contents($php_config_file, $content);
}
