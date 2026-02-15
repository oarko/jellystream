<?php
require_once 'config/config.php';
require_once 'config/ports.php';
require_once 'includes/database.php';

$db = new Database();
$message = '';
$message_type = '';

// Handle form submission
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $config = [
        'APP_NAME' => $_POST['app_name'] ?? 'JellyStream',
        'DEBUG' => $_POST['debug'] ?? 'False',
        'HOST' => $_POST['host'] ?? '0.0.0.0',
        'PORT' => $_POST['api_port'] ?? '8000',
        'DATABASE_URL' => $_POST['database_url'] ?? 'sqlite:///./data/database/jellystream.db',
        'JELLYFIN_URL' => $_POST['jellyfin_url'] ?? '',
        'JELLYFIN_API_KEY' => $_POST['jellyfin_api_key'] ?? '',
        'JELLYFIN_USER_ID' => $_POST['jellyfin_user_id'] ?? '',
        'JELLYFIN_CLIENT_NAME' => $_POST['jellyfin_client_name'] ?? 'JellyStream',
        'JELLYFIN_DEVICE_NAME' => $_POST['jellyfin_device_name'] ?? 'JellyStream Server',
        'LOG_LEVEL' => $_POST['log_level'] ?? 'INFO',
        'LOG_TO_FILE' => $_POST['log_to_file'] ?? 'True',
        'LOG_RETENTION_DAYS' => $_POST['log_retention_days'] ?? '30',
    ];

    // Save port configuration separately
    $php_port = $_POST['php_port'] ?? 8080;
    $api_port = $_POST['api_port'] ?? 8000;

    $success = true;

    if (!$db->saveEnvConfig($config)) {
        $success = false;
    }

    if (!savePortConfig($php_port, $api_port)) {
        $success = false;
    }

    if ($success) {
        $message = 'Configuration saved successfully! Please restart both services for changes to take effect.';
        $message_type = 'success';
    } else {
        $message = 'Error saving configuration.';
        $message_type = 'error';
    }
}

// Load current config
$current_config = $db->getEnvConfig();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JellyStream Setup</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #181818;
            color: #fff;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .card {
            background: #282828;
            border-radius: 8px;
            padding: 30px;
            margin-bottom: 20px;
        }
        h1, h2 {
            color: #00A4DC;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #B3B3B3;
        }
        input, select {
            width: 100%;
            padding: 10px;
            background: #1F1F1F;
            border: 1px solid #444;
            color: #fff;
            border-radius: 5px;
            box-sizing: border-box;
        }
        .btn {
            background: #00A4DC;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        .btn:hover {
            opacity: 0.9;
        }
        .message {
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .message.success {
            background: #28a745;
        }
        .message.error {
            background: #dc3545;
        }
        .back-link {
            color: #00A4DC;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>⚙️ JellyStream Setup</h1>
            <?php if ($message): ?>
                <div class="message <?php echo $message_type; ?>">
                    <?php echo htmlspecialchars($message); ?>
                </div>
            <?php endif; ?>

            <form method="POST">
                <h2>Application Settings</h2>

                <div class="form-group">
                    <label for="app_name">Application Name</label>
                    <input type="text" id="app_name" name="app_name"
                           value="<?php echo htmlspecialchars($current_config['APP_NAME'] ?? 'JellyStream'); ?>">
                </div>

                <div class="form-group">
                    <label for="debug">Debug Mode</label>
                    <select id="debug" name="debug">
                        <option value="False" <?php echo ($current_config['DEBUG'] ?? 'False') == 'False' ? 'selected' : ''; ?>>False</option>
                        <option value="True" <?php echo ($current_config['DEBUG'] ?? '') == 'True' ? 'selected' : ''; ?>>True</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="host">Server Host</label>
                    <input type="text" id="host" name="host"
                           value="<?php echo htmlspecialchars($current_config['HOST'] ?? '0.0.0.0'); ?>">
                </div>

                <h2>Port Configuration</h2>

                <div class="form-group">
                    <label for="php_port">PHP Frontend Port</label>
                    <input type="number" id="php_port" name="php_port"
                           value="<?php echo defined('PHP_FRONTEND_PORT') ? PHP_FRONTEND_PORT : 8080; ?>"
                           min="1024" max="65535">
                    <small style="color: #B3B3B3;">Port for the PHP web interface (default: 8080)</small>
                </div>

                <div class="form-group">
                    <label for="api_port">API Backend Port</label>
                    <input type="number" id="api_port" name="api_port"
                           value="<?php echo defined('API_BACKEND_PORT') ? API_BACKEND_PORT : ($current_config['PORT'] ?? 8000); ?>"
                           min="1024" max="65535">
                    <small style="color: #B3B3B3;">Port for the FastAPI backend (default: 8000)</small>
                </div>

                <h2>Jellyfin Configuration</h2>

                <div class="form-group">
                    <label for="jellyfin_url">Jellyfin URL</label>
                    <input type="url" id="jellyfin_url" name="jellyfin_url"
                           placeholder="http://localhost:8096"
                           value="<?php echo htmlspecialchars($current_config['JELLYFIN_URL'] ?? ''); ?>">
                </div>

                <div class="form-group">
                    <label for="jellyfin_api_key">Jellyfin API Key</label>
                    <input type="text" id="jellyfin_api_key" name="jellyfin_api_key"
                           placeholder="Your API key"
                           value="<?php echo htmlspecialchars($current_config['JELLYFIN_API_KEY'] ?? ''); ?>">
                </div>

                <div class="form-group">
                    <label for="jellyfin_user_id">Jellyfin User ID (Optional)</label>
                    <input type="text" id="jellyfin_user_id" name="jellyfin_user_id"
                           placeholder="Auto-detected if left empty"
                           value="<?php echo htmlspecialchars($current_config['JELLYFIN_USER_ID'] ?? ''); ?>">
                    <small style="color: #888;">Get your user ID from <a href="/api/jellyfin/users" target="_blank" style="color: #00A4DC;">/api/jellyfin/users</a> (after saving URL and API key)</small>
                </div>

                <div class="form-group">
                    <label for="jellyfin_client_name">Client Name</label>
                    <input type="text" id="jellyfin_client_name" name="jellyfin_client_name"
                           value="<?php echo htmlspecialchars($current_config['JELLYFIN_CLIENT_NAME'] ?? 'JellyStream'); ?>">
                </div>

                <div class="form-group">
                    <label for="jellyfin_device_name">Device Name</label>
                    <input type="text" id="jellyfin_device_name" name="jellyfin_device_name"
                           value="<?php echo htmlspecialchars($current_config['JELLYFIN_DEVICE_NAME'] ?? 'JellyStream Server'); ?>">
                </div>

                <h2>Logging Configuration</h2>

                <div class="form-group">
                    <label for="log_level">Log Level</label>
                    <select id="log_level" name="log_level">
                        <?php
                        $levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
                        $current_level = $current_config['LOG_LEVEL'] ?? 'INFO';
                        foreach ($levels as $level):
                        ?>
                            <option value="<?php echo $level; ?>" <?php echo $level == $current_level ? 'selected' : ''; ?>>
                                <?php echo $level; ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>

                <div class="form-group">
                    <label for="log_to_file">Log to File</label>
                    <select id="log_to_file" name="log_to_file">
                        <option value="True" <?php echo ($current_config['LOG_TO_FILE'] ?? 'True') == 'True' ? 'selected' : ''; ?>>Yes</option>
                        <option value="False" <?php echo ($current_config['LOG_TO_FILE'] ?? '') == 'False' ? 'selected' : ''; ?>>No</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="log_retention_days">Log Retention (Days)</label>
                    <input type="number" id="log_retention_days" name="log_retention_days"
                           value="<?php echo htmlspecialchars($current_config['LOG_RETENTION_DAYS'] ?? '30'); ?>">
                </div>

                <button type="submit" class="btn">💾 Save Configuration</button>
                <a href="index.php" class="back-link">← Back to Dashboard</a>
            </form>
        </div>
    </div>
</body>
</html>
