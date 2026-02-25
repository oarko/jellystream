<?php
require_once '../config/config.php';
require_once '../includes/api_client.php';

$api = new ApiClient();

// Handle delete
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action'])) {
    if ($_POST['action'] === 'delete' && isset($_POST['channel_id'])) {
        $api->deleteChannel(intval($_POST['channel_id']));
        header('Location: channels.php');
        exit;
    }
    if ($_POST['action'] === 'generate' && isset($_POST['channel_id'])) {
        $api->generateChannelSchedule(intval($_POST['channel_id']));
        header('Location: channels.php?generated=1');
        exit;
    }
}

$response = $api->getChannels();
$channels = $response['success'] ? ($response['data'] ?? []) : [];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Channels - <?php echo APP_NAME; ?></title>
    <link rel="stylesheet" href="/static/css/style.css">
    <style>
        body { font-family: Arial, sans-serif; background: #181818; color: #fff; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #1F1F1F; padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { margin: 0; color: #00A4DC; }
        .btn { padding: 8px 16px; border-radius: 4px; border: none; cursor: pointer; font-size: 14px; text-decoration: none; display: inline-block; }
        .btn-primary { background: #00A4DC; color: #fff; }
        .btn-danger  { background: #c0392b; color: #fff; }
        .btn-secondary { background: #444; color: #fff; }
        .btn-success { background: #27ae60; color: #fff; }
        table { width: 100%; border-collapse: collapse; background: #1F1F1F; border-radius: 8px; overflow: hidden; }
        th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid #333; }
        th { background: #2a2a2a; color: #aaa; font-weight: 600; font-size: 13px; text-transform: uppercase; }
        tr:last-child td { border-bottom: none; }
        .badge { padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        .badge-auto { background: #0d47a1; color: #90caf9; }
        .badge-manual { background: #424242; color: #bbb; }
        .badge-on { background: #1b5e20; color: #a5d6a7; }
        .badge-off { background: #b71c1c; color: #ef9a9a; }
        .ch-num { font-family: monospace; color: #aaa; }
        .actions { display: flex; gap: 6px; flex-wrap: wrap; }
        .alert { padding: 12px 16px; border-radius: 6px; margin-bottom: 16px; }
        .alert-success { background: #1b5e20; color: #a5d6a7; }
        .libs { font-size: 12px; color: #888; }
        @media(max-width:640px) {
            .header { flex-direction: column; align-items: flex-start; gap: 10px; }
            .header > div { width: 100%; flex-wrap: wrap; }
            /* Hide the Libraries column on small screens */
            th:nth-child(4), td:nth-child(4) { display: none; }
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📺 Channels</h1>
        <div style="display:flex;gap:8px;">
            <a href="../index.php" class="btn btn-secondary">← Dashboard</a>
            <a href="channel_edit.php" class="btn btn-primary">+ New Channel</a>
        </div>
    </div>

    <?php if (isset($_GET['generated'])): ?>
        <div class="alert alert-success">Schedule generation triggered successfully.</div>
    <?php endif; ?>

    <?php if (empty($channels)): ?>
        <div style="background:#1F1F1F;padding:40px;border-radius:8px;text-align:center;color:#888;">
            No channels yet. <a href="channel_edit.php" style="color:#00A4DC;">Create your first channel →</a>
        </div>
    <?php else: ?>
    <div class="table-scroll">
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Name</th>
                <th>Schedule</th>
                <th>Libraries</th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($channels as $ch): ?>
            <tr>
                <td class="ch-num"><?php echo htmlspecialchars($ch['channel_number'] ?? '—'); ?></td>
                <td>
                    <strong><?php echo htmlspecialchars($ch['name']); ?></strong><br>
                    <small style="color:#888;"><?php echo htmlspecialchars($ch['description'] ?? ''); ?></small>
                </td>
                <td>
                    <?php if ($ch['schedule_type'] === 'genre_auto'): ?>
                        <span class="badge badge-auto">Auto</span>
                    <?php else: ?>
                        <span class="badge badge-manual">Manual</span>
                    <?php endif; ?>
                </td>
                <td class="libs">
                    <?php
                    $libs = $ch['libraries'] ?? [];
                    if ($libs) {
                        echo implode(', ', array_map(fn($l) => htmlspecialchars($l['library_name']), $libs));
                    } else {
                        echo '<em style="color:#555">None</em>';
                    }
                    ?>
                </td>
                <td>
                    <?php if ($ch['enabled']): ?>
                        <span class="badge badge-on">Enabled</span>
                    <?php else: ?>
                        <span class="badge badge-off">Disabled</span>
                    <?php endif; ?>
                </td>
                <td>
                    <div class="actions">
                        <a href="channel_edit.php?id=<?php echo $ch['id']; ?>" class="btn btn-secondary" style="font-size:12px;">Edit</a>
                        <form method="POST" style="display:inline;" onsubmit="return confirm('Generate schedule for this channel?');">
                            <input type="hidden" name="action" value="generate">
                            <input type="hidden" name="channel_id" value="<?php echo $ch['id']; ?>">
                            <button type="submit" class="btn btn-success" style="font-size:12px;">Generate</button>
                        </form>
                        <form method="POST" style="display:inline;" onsubmit="return confirm('Delete channel \'<?php echo addslashes($ch['name']); ?>\'?');">
                            <input type="hidden" name="action" value="delete">
                            <input type="hidden" name="channel_id" value="<?php echo $ch['id']; ?>">
                            <button type="submit" class="btn btn-danger" style="font-size:12px;">Delete</button>
                        </form>
                    </div>
                </td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    </div><!-- /.table-scroll -->
    <?php endif; ?>
</div>
</body>
</html>
