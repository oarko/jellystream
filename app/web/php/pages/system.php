<?php
require_once '../config/config.php';
require_once '../includes/api_client.php';

$api = new ApiClient();

$version_resp = $api->getSystemVersion();
$version = $version_resp['success'] ? ($version_resp['data'] ?? []) : [];
$current_channel = $version['channel'] ?? 'main';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Updates - <?php echo APP_NAME; ?></title>
    <link rel="stylesheet" href="/static/css/style.css">
    <style>
        .version-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #2a2a2a; font-size: 14px; }
        .version-row:last-child { border-bottom: none; }
        .version-label { color: #888; }
        .version-value { color: #fff; font-family: monospace; }
        .dirty-warning { background: #7f2700; color: #ffccbc; padding: 10px 14px; border-radius: 6px; font-size: 13px; margin-top: 12px; }
        .channel-options { display: flex; gap: 20px; margin: 12px 0; }
        .channel-options label { display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 14px; }
        #check-result { margin-top: 16px; padding: 14px; border-radius: 6px; font-size: 14px; display: none; }
        #check-result.up-to-date { background: #1b5e20; color: #a5d6a7; display: block; }
        #check-result.available  { background: #0d47a1; color: #90caf9; display: block; }
        #check-result.error      { background: #7f2700; color: #ffccbc; display: block; }
        .cmd-box { background: #111; border: 1px solid #333; border-radius: 6px; padding: 12px 14px; font-family: monospace; font-size: 13px; color: #a5d6a7; margin-top: 8px; overflow-x: auto; }
        #status-msg { margin-top: 14px; padding: 10px 14px; border-radius: 6px; display: none; font-size: 14px; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="header-left">
            <h1>Updates</h1>
            <p>Check and apply JellyStream updates from GitHub</p>
        </div>
        <div class="header-right">
            <a href="../index.php" class="btn btn-secondary">← Dashboard</a>
        </div>
    </div>

    <div class="card">
        <h2>Current Version</h2>
        <?php if (!$version || !($version['git_available'] ?? false)): ?>
            <p style="color:#888;">Version info unavailable — this doesn't look like a git checkout.</p>
        <?php else: ?>
            <div class="version-row">
                <span class="version-label">Branch</span>
                <span class="version-value"><?php echo htmlspecialchars($version['branch'] ?? '—'); ?></span>
            </div>
            <div class="version-row">
                <span class="version-label">Commit</span>
                <span class="version-value"><?php echo htmlspecialchars($version['commit_short'] ?? '—'); ?></span>
            </div>
            <div class="version-row">
                <span class="version-label">Commit Date</span>
                <span class="version-value"><?php echo htmlspecialchars($version['commit_date'] ?? '—'); ?></span>
            </div>
            <?php if (!empty($version['dirty'])): ?>
            <div class="dirty-warning">
                ⚠️ This checkout has local modifications. <code>./update.sh</code> will refuse to run until
                they're committed, stashed, or discarded.
            </div>
            <?php endif; ?>
        <?php endif; ?>
    </div>

    <div class="card">
        <h2>Update Channel</h2>
        <div class="hint" style="margin-bottom:8px;">
            <strong>main</strong> is the stable release branch. <strong>nightly</strong> tracks the latest
            changes and may be less stable. This is what <code>./update.sh</code> pulls from by default,
            and what "Check for Updates" below compares against.
        </div>
        <div class="channel-options">
            <label>
                <input type="radio" name="channel" value="main" <?php echo $current_channel === 'main' ? 'checked' : ''; ?>>
                main (stable)
            </label>
            <label>
                <input type="radio" name="channel" value="nightly" <?php echo $current_channel === 'nightly' ? 'checked' : ''; ?>>
                nightly (latest)
            </label>
        </div>
        <button class="btn btn-primary" onclick="saveChannel()">Save Channel</button>
        <div id="status-msg"></div>
    </div>

    <div class="card">
        <h2>Check for Updates</h2>
        <button class="btn btn-primary" onclick="checkForUpdates()" id="check-btn">Check Now</button>
        <div id="check-result"></div>
    </div>

    <div class="card">
        <h2>Applying an Update</h2>
        <div class="hint">
            JellyStream's own service account can't modify its own code (intentionally — see
            <code>deploy/README.md</code>), so updates are applied by you, as the admin, from the
            command line:
        </div>
        <div class="cmd-box">cd <?php echo htmlspecialchars(dirname(dirname(dirname(dirname(__DIR__))))); ?><br>./update.sh</div>
        <div class="hint" style="margin-top:10px;">
            This fetches the latest code on your selected channel, reinstalls Python dependencies if
            <code>requirements.txt</code> changed, and restarts the systemd services (if installed).
            It refuses to run if there are uncommitted local changes, and it will never force-overwrite
            history that has diverged from GitHub.
        </div>
    </div>
</div>

<script>
const API_BASE = '<?php echo getClientApiBaseUrl(); ?>';

async function saveChannel() {
    const channel = document.querySelector('input[name="channel"]:checked').value;
    const statusEl = document.getElementById('status-msg');
    try {
        const resp = await fetch(`${API_BASE}/system/update-channel`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ channel }),
        });
        const data = await resp.json();
        statusEl.style.display = 'block';
        if (resp.ok) {
            statusEl.className = 'status-ok';
            statusEl.textContent = `Channel set to "${channel}". Run ./update.sh (no argument) to use it.`;
        } else {
            statusEl.className = 'status-err';
            statusEl.textContent = data.detail || 'Failed to save channel.';
        }
    } catch (e) {
        statusEl.style.display = 'block';
        statusEl.className = 'status-err';
        statusEl.textContent = 'Network error: ' + e.message;
    }
}

async function checkForUpdates() {
    const btn = document.getElementById('check-btn');
    const resultEl = document.getElementById('check-result');
    const channel = document.querySelector('input[name="channel"]:checked').value;
    btn.disabled = true;
    btn.textContent = 'Checking...';
    resultEl.style.display = 'none';

    try {
        const resp = await fetch(`${API_BASE}/system/update-check?channel=${encodeURIComponent(channel)}`);
        const data = await resp.json();
        if (!resp.ok) {
            resultEl.className = 'error';
            resultEl.textContent = data.detail || 'Check failed.';
        } else if (data.update_available) {
            resultEl.className = 'available';
            resultEl.innerHTML = `Update available on <strong>${esc(data.channel)}</strong>: ` +
                `${esc(data.latest_commit_short)} — ${esc(data.latest_commit_message || '')} ` +
                `(you're on ${esc(data.local_commit_short)}). Run <code>./update.sh</code> to apply it.`;
        } else {
            resultEl.className = 'up-to-date';
            resultEl.textContent = `You're up to date on ${data.channel} (${data.local_commit_short}).`;
        }
    } catch (e) {
        resultEl.className = 'error';
        resultEl.textContent = 'Network error: ' + e.message;
    }

    resultEl.style.display = 'block';
    btn.disabled = false;
    btn.textContent = 'Check Now';
}

function esc(s) {
    return String(s ?? '')
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
</script>
</body>
</html>
