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
} else {
    // Use defaults
    define('PHP_FRONTEND_PORT', $DEFAULT_PHP_PORT);
    define('API_BACKEND_PORT', $DEFAULT_API_PORT);
}

/**
 * Get the full API URL based on configured port
 */
function getApiBaseUrl() {
    return 'http://localhost:' . API_BACKEND_PORT . '/api';
}

/**
 * Save port configuration
 */
function savePortConfig($php_port, $api_port) {
    $php_config_file = __DIR__ . '/../.phpconfig';
    $config = [
        'PHP_FRONTEND_PORT' => $php_port,
        'API_BACKEND_PORT' => $api_port
    ];

    $content = "; JellyStream PHP Configuration\n";
    $content .= "; Auto-generated - do not edit manually\n\n";
    foreach ($config as $key => $value) {
        $content .= "$key=$value\n";
    }

    return file_put_contents($php_config_file, $content);
}
