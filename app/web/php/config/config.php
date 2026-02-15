<?php
/**
 * JellyStream PHP Configuration
 */

// Load port configuration
require_once __DIR__ . '/ports.php';

// API Configuration
define('API_BASE_URL', getApiBaseUrl());
define('API_TIMEOUT', 30);

// Database Configuration
define('DB_PATH', __DIR__ . '/../../../../data/database/jellystream.db');

// Application Settings
define('APP_NAME', 'JellyStream');
define('APP_VERSION', '0.1.0');

// Session Configuration
ini_set('session.cookie_httponly', 1);
ini_set('session.use_strict_mode', 1);
session_start();

// Error Reporting (set to 0 in production)
error_reporting(E_ALL);
ini_set('display_errors', 1);
