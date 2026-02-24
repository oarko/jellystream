<?php
require_once 'config/config.php';
require_once 'includes/api_client.php';

$api = new ApiClient();

// Redirect to setup if .env is missing
$env_file = __DIR__ . '/../../../.env';
if (!file_exists($env_file)) {
    header('Location: setup.php');
    exit;
}

// Fetch channels and now-playing info
$channels_response = $api->getChannels();
$channels = $channels_response['success'] ? ($channels_response['data'] ?? []) : [];

$now_playing = [];
foreach ($channels as $ch) {
    $resp = $api->getNowPlaying($ch['id']);
    if ($resp['success'] && !empty($resp['data'])) {
        $now_playing[$ch['id']] = $resp['data'];
    }
}

$health = $api->healthCheck();
$api_ok = $health['success'] && ($health['data']['status'] ?? '') === 'healthy';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo APP_NAME; ?> - Dashboard</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <style>
        body { font-family: Arial, sans-serif; background: #181818; color: #fff; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #1F1F1F; padding: 20px 24px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        .header-left h1 { margin: 0 0 4px; color: #00A4DC; font-size: 28px; }
        .header-left p  { margin: 0; color: #888; font-size: 14px; }
        .header-right { display: flex; gap: 10px; align-items: center; }
        .api-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px; }
        .api-ok  { background: #27ae60; }
        .api-err { background: #c0392b; }
        .card { background: #1F1F1F; border-radius: 8px; padding: 20px 24px; margin-bottom: 20px; }
        .card h2 { margin: 0 0 16px; color: #ccc; font-size: 16px; border-bottom: 1px solid #333; padding-bottom: 8px; }
        .btn { background: #00A4DC; color: #fff; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; font-size: 14px; }
        .btn:hover { opacity: .9; }
        .btn-sm { padding: 5px 10px; font-size: 12px; }
        .btn-secondary { background: #444; }
        /* Channel grid */
        .channel-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }
        .ch-card { background: #242424; border-radius: 8px; padding: 16px; border-left: 3px solid #00A4DC; }
        .ch-card.disabled { border-left-color: #555; opacity: .7; }
        .ch-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
        .ch-name { font-size: 16px; font-weight: 600; }
        .ch-num  { font-family: monospace; color: #888; font-size: 13px; }
        .now-playing { background: #1a1a2e; border-radius: 6px; padding: 10px 12px; font-size: 13px; }
        .np-label { color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 3px; }
        .np-title { color: #fff; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .np-sub   { color: #888; font-size: 12px; margin-top: 2px; }
        .np-progress { height: 3px; background: #333; border-radius: 2px; margin-top: 8px; }
        .np-bar   { height: 100%; background: #00A4DC; border-radius: 2px; }
        .no-schedule { color: #555; font-size: 13px; font-style: italic; padding: 8px 0; }
        .badge { padding: 3px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
        .badge-auto   { background: #0d47a1; color: #90caf9; }
        .badge-manual { background: #424242; color: #bbb; }
        .badge-reg    { background: #1b5e20; color: #a5d6a7; }
        .ch-actions { display: flex; gap: 6px; margin-top: 12px; }
        /* Quick links */
        .links { display: flex; flex-wrap: wrap; gap: 10px; }
        .link-btn { background: #2a2a2a; color: #ccc; padding: 8px 14px; border-radius: 6px; text-decoration: none; font-size: 13px; border: 1px solid #333; }
        .link-btn:hover { border-color: #00A4DC; color: #00A4DC; }
        .empty-state { text-align: center; padding: 40px; color: #555; }
        .empty-state a { color: #00A4DC; }
    </style>
</head>
<body>
<div class="container">
    <!-- Header -->
    <div class="header">
        <div class="header-left">
            <h1>📺 <?php echo APP_NAME; ?></h1>
            <p>Virtual TV channel generator for Jellyfin</p>
        </div>
        <div class="header-right">
            <span style="font-size:13px;color:#888;">
                <span class="api-dot <?php echo $api_ok ? 'api-ok' : 'api-err'; ?>"></span>
                API <?php echo $api_ok ? 'online' : 'offline'; ?>
            </span>
            <a href="setup.php" class="btn btn-secondary">⚙ Settings</a>
            <a href="pages/channels.php" class="btn">+ New Channel</a>
        </div>
    </div>

    <!-- Channel grid -->
    <div class="card">
        <h2>Channels
            <span style="color:#555;font-weight:400;font-size:13px;margin-left:8px;"><?php echo count($channels); ?> total</span>
        </h2>

        <?php if (empty($channels)): ?>
        <div class="empty-state">
            No channels yet.<br>
            <a href="pages/channels.php">Create your first channel →</a>
        </div>
        <?php else: ?>
        <div class="channel-grid">
            <?php foreach ($channels as $ch):
                $np = $now_playing[$ch['id']] ?? null;
                $duration = $np['duration'] ?? 0;
                $offset   = $np['current_offset_seconds'] ?? 0;
                $pct      = $duration > 0 ? min(100, round($offset / $duration * 100)) : 0;
            ?>
            <div class="ch-card <?php echo $ch['enabled'] ? '' : 'disabled'; ?>">
                <div class="ch-header">
                    <div>
                        <div class="ch-name"><?php echo htmlspecialchars($ch['name']); ?></div>
                        <div class="ch-num">Ch <?php echo htmlspecialchars($ch['channel_number'] ?? '—'); ?></div>
                    </div>
                    <div style="display:flex;gap:5px;flex-wrap:wrap;justify-content:flex-end;">
                        <?php if ($ch['schedule_type'] === 'genre_auto'): ?>
                            <span class="badge badge-auto">Auto</span>
                        <?php else: ?>
                            <span class="badge badge-manual">Manual</span>
                        <?php endif; ?>
                        <?php if (!empty($ch['tuner_host_id'])): ?>
                            <span class="badge badge-reg">Live TV</span>
                        <?php endif; ?>
                    </div>
                </div>

                <?php if ($np): ?>
                <div class="now-playing">
                    <div class="np-label">Now Playing</div>
                    <div class="np-title"><?php echo htmlspecialchars($np['title']); ?></div>
                    <?php if (!empty($np['series_name'])): ?>
                    <div class="np-sub">
                        <?php echo htmlspecialchars($np['series_name']); ?>
                        <?php if ($np['season_number'] && $np['episode_number']): ?>
                            S<?php echo $np['season_number']; ?>E<?php echo $np['episode_number']; ?>
                        <?php endif; ?>
                    </div>
                    <?php endif; ?>
                    <div class="np-progress"><div class="np-bar" style="width:<?php echo $pct; ?>%"></div></div>
                    <div style="font-size:11px;color:#555;margin-top:4px;display:flex;justify-content:space-between;">
                        <span><?php echo gmdate('H:i:s', $offset); ?></span>
                        <span><?php echo gmdate('H:i:s', $duration); ?></span>
                    </div>
                </div>
                <?php else: ?>
                <div class="no-schedule">Nothing scheduled right now</div>
                <?php endif; ?>

                <div class="ch-actions">
                    <a href="pages/channel_edit.php?id=<?php echo $ch['id']; ?>" class="btn btn-secondary btn-sm">Edit</a>
                    <?php if ($ch['enabled']): ?>
                    <a href="<?php echo getClientApiBaseUrl(); ?>/livetv/stream/<?php echo $ch['id']; ?>" class="btn btn-sm" target="_blank">▶ Stream</a>
                    <?php endif; ?>
                    <a href="<?php echo getClientApiBaseUrl(); ?>/livetv/m3u/<?php echo $ch['id']; ?>" class="btn btn-secondary btn-sm" target="_blank">M3U</a>
                </div>
            </div>
            <?php endforeach; ?>
        </div>
        <?php endif; ?>
    </div>

    <!-- Quick links -->
    <div class="card">
        <h2>Quick Links</h2>
        <div class="links">
            <a href="pages/channels.php"                          class="link-btn">📋 All Channels</a>
            <a href="pages/collections.php"                       class="link-btn">📦 Collections</a>
            <a href="<?php echo getClientApiBaseUrl(); ?>/livetv/m3u/all"   class="link-btn" target="_blank">📄 M3U Playlist</a>
            <a href="<?php echo getClientApiBaseUrl(); ?>/livetv/xmltv/all" class="link-btn" target="_blank">📅 XMLTV EPG</a>
            <a href="/docs"                                        class="link-btn" target="_blank">📖 API Docs</a>
            <a href="/health"                                      class="link-btn" target="_blank">❤ Health</a>
        </div>
    </div>
</div>
</body>
</html>
