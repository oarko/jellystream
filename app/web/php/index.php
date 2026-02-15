<?php
require_once 'config/config.php';
require_once 'includes/api_client.php';
require_once 'includes/database.php';

$api = new ApiClient();
$db = new Database();

// Check if .env exists
$env_file = __DIR__ . '/../../../.env';
$needs_setup = !file_exists($env_file);

if ($needs_setup) {
    header('Location: setup.php');
    exit;
}

// Get streams from API
$streams_response = $api->getStreams();
$streams = $streams_response['success'] ? $streams_response['data'] : [];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo APP_NAME; ?> - Dashboard</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #181818;
            color: #fff;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: #1F1F1F;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .card {
            background: #282828;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .btn {
            background: #00A4DC;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover {
            opacity: 0.9;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #444;
        }
        .status-badge {
            padding: 5px 10px;
            border-radius: 3px;
            font-size: 12px;
        }
        .status-enabled {
            background: #28a745;
        }
        .status-disabled {
            background: #dc3545;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><?php echo APP_NAME; ?></h1>
            <p>Media Streaming Integration for Jellyfin</p>
            <a href="setup.php" class="btn">⚙️ Settings</a>
            <a href="pages/streams.php" class="btn">📺 Manage Streams</a>
        </div>

        <div class="card">
            <h2>Streams Overview</h2>
            <?php if (empty($streams)): ?>
                <p>No streams configured yet.</p>
                <a href="pages/streams.php" class="btn">Create Your First Stream</a>
            <?php else: ?>
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Description</th>
                            <th>Status</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($streams as $stream): ?>
                        <tr>
                            <td><?php echo htmlspecialchars($stream['name']); ?></td>
                            <td><?php echo htmlspecialchars($stream['description'] ?? 'N/A'); ?></td>
                            <td>
                                <span class="status-badge status-<?php echo $stream['enabled'] ? 'enabled' : 'disabled'; ?>">
                                    <?php echo $stream['enabled'] ? 'Enabled' : 'Disabled'; ?>
                                </span>
                            </td>
                            <td><?php echo date('Y-m-d H:i', strtotime($stream['created_at'])); ?></td>
                            <td>
                                <a href="pages/stream_detail.php?id=<?php echo $stream['id']; ?>" class="btn">View</a>
                            </td>
                        </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            <?php endif; ?>
        </div>

        <div class="card">
            <h3>Quick Links</h3>
            <ul>
                <li><a href="/docs">API Documentation</a></li>
                <li><a href="/api">API Root</a></li>
                <li><a href="/health">Health Check</a></li>
            </ul>
        </div>
    </div>
</body>
</html>
