<?php
require_once '../config/config.php';
require_once '../includes/api_client.php';

$api = new ApiClient();

// Get all streams
$streams_response = $api->getStreams();
$streams = $streams_response['success'] ? $streams_response['data'] : [];

// Get libraries for display
$libraries_response = $api->getJellyfinLibraries();
$libraries = $libraries_response['success'] && isset($libraries_response['data']['libraries'])
    ? $libraries_response['data']['libraries']
    : [];

// Create library lookup map
$library_map = [];
foreach ($libraries as $library) {
    $library_map[$library['Id']] = $library['Name'];
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Manage Streams - <?php echo APP_NAME; ?></title>
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
            display: flex;
            justify-content: space-between;
            align-items: center;
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
            margin-right: 10px;
        }
        .btn:hover {
            opacity: 0.9;
        }
        .btn-secondary {
            background: #555;
        }
        .btn-danger {
            background: #dc3545;
        }
        .btn-success {
            background: #28a745;
        }
        .btn-sm {
            padding: 5px 10px;
            font-size: 13px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #444;
        }
        th {
            color: #00A4DC;
            font-weight: bold;
        }
        .status-badge {
            padding: 5px 10px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-enabled {
            background: #28a745;
        }
        .status-disabled {
            background: #dc3545;
        }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #888;
        }
        .empty-state h3 {
            color: #fff;
            margin-bottom: 10px;
        }
        .stream-actions {
            display: flex;
            gap: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>📺 Manage Streams</h1>
                <p style="margin: 5px 0 0 0; color: #888;">Create and configure your streaming channels</p>
            </div>
            <div>
                <a href="/index.php" class="btn btn-secondary">← Back</a>
                <a href="stream_edit.php" class="btn btn-success">+ Create Stream</a>
            </div>
        </div>

        <div class="card">
            <?php if (empty($streams)): ?>
                <div class="empty-state">
                    <h3>No Streams Yet</h3>
                    <p>Get started by creating your first streaming channel</p>
                    <br>
                    <a href="stream_edit.php" class="btn btn-success">+ Create Your First Stream</a>
                </div>
            <?php else: ?>
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Library</th>
                            <th>Description</th>
                            <th>Status</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($streams as $stream): ?>
                        <tr>
                            <td><strong><?php echo htmlspecialchars($stream['name']); ?></strong></td>
                            <td>
                                <?php
                                $lib_id = $stream['jellyfin_library_id'];
                                echo htmlspecialchars($library_map[$lib_id] ?? $lib_id);
                                ?>
                            </td>
                            <td><?php echo htmlspecialchars($stream['description'] ?? 'N/A'); ?></td>
                            <td>
                                <span class="status-badge status-<?php echo $stream['enabled'] ? 'enabled' : 'disabled'; ?>">
                                    <?php echo $stream['enabled'] ? '✓ Enabled' : '✗ Disabled'; ?>
                                </span>
                            </td>
                            <td><?php echo date('M j, Y', strtotime($stream['created_at'])); ?></td>
                            <td>
                                <div class="stream-actions">
                                    <a href="stream_edit.php?id=<?php echo $stream['id']; ?>" class="btn btn-sm">Edit</a>
                                    <button class="btn btn-danger btn-sm"
                                            onclick="deleteStream(<?php echo $stream['id']; ?>, '<?php echo htmlspecialchars($stream['name']); ?>')">
                                        Delete
                                    </button>
                                </div>
                            </td>
                        </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            <?php endif; ?>
        </div>
    </div>

    <script>
        async function deleteStream(id, name) {
            if (!confirm(`Are you sure you want to delete "${name}"?\n\nThis will also delete all scheduled items for this stream.`)) {
                return;
            }

            try {
                const response = await fetch(`<?php echo API_BASE_URL; ?>/streams/${id}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    location.reload();
                } else {
                    const result = await response.json();
                    alert('Error deleting stream: ' + (result.detail || 'Unknown error'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error deleting stream');
            }
        }
    </script>
</body>
</html>
