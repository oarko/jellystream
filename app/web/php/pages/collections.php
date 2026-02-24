<?php
require_once '../config/config.php';
require_once '../includes/api_client.php';

$api = new ApiClient();

// Handle delete via POST
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action'])) {
    if ($_POST['action'] === 'delete' && isset($_POST['collection_id'])) {
        $api->deleteCollection(intval($_POST['collection_id']));
        header('Location: collections.php?deleted=1');
        exit;
    }
}

$response   = $api->getCollections();
$collections = $response['success'] ? ($response['data'] ?? []) : [];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Collections - <?php echo APP_NAME; ?></title>
    <link rel="stylesheet" href="/static/css/style.css">
    <style>
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid #2a2a2a; }
        th { color: #aaa; font-weight: 600; font-size: 13px; text-transform: uppercase; letter-spacing: .5px; }
        tr:hover td { background: #232323; }
        .badge-jellyfin { background: #004a8f; color: #90caf9; }
        .badge-custom   { background: #2e2e2e; color: #ccc; }
        .actions { display: flex; gap: 6px; flex-wrap: wrap; }
        .modal-overlay { display:none; position:fixed; inset:0; background:rgba(0,0,0,.7); z-index:100; align-items:center; justify-content:center; }
        .modal-overlay.open { display:flex; }
        .modal { background:#1f1f1f; border-radius:10px; padding:24px; width:480px; max-width:95vw; max-height:80vh; overflow-y:auto; }
        .modal h2 { margin:0 0 16px; font-size:18px; color:#fff; }
        .boxset-list { list-style:none; padding:0; margin:0; }
        .boxset-list li { display:flex; align-items:center; justify-content:space-between; padding:10px 12px; border-radius:6px; cursor:pointer; transition:background .15s; }
        .boxset-list li:hover { background:#2a2a2a; }
        .boxset-name { color:#fff; font-size:14px; }
        .verify-results { margin-top:10px; font-size:13px; }
        .v-ok      { color:#81c784; }
        .v-moved   { color:#ffb74d; }
        .v-deleted { color:#e57373; }
        .v-nopath  { color:#888; }
        #status-msg { margin-bottom:14px; padding:10px 14px; border-radius:6px; display:none; font-size:14px; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📦 Collections</h1>
        <div style="display:flex;gap:8px;">
            <a href="../index.php" class="btn btn-secondary">← Dashboard</a>
            <button class="btn btn-secondary" onclick="openImportModal()">⬇ Import Boxset</button>
            <a href="collection_edit.php" class="btn btn-primary">+ New Collection</a>
        </div>
    </div>

    <div id="status-msg"></div>

    <?php if (isset($_GET['deleted'])): ?>
        <div class="status-ok" style="padding:10px 14px;border-radius:6px;margin-bottom:14px;">Collection deleted.</div>
    <?php endif; ?>

    <div class="card">
        <?php if (empty($collections)): ?>
            <p style="color:#888;text-align:center;padding:32px 0;">
                No collections yet. Create one or import a Jellyfin boxset.
            </p>
        <?php else: ?>
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Source</th>
                    <th style="text-align:center;">Items</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
            <?php foreach ($collections as $col): ?>
                <tr>
                    <td>
                        <strong><?php echo htmlspecialchars($col['name']); ?></strong>
                        <?php if (!empty($col['description'])): ?>
                            <br><small style="color:#888;"><?php echo htmlspecialchars($col['description']); ?></small>
                        <?php endif; ?>
                    </td>
                    <td>
                        <?php if (!empty($col['jellyfin_id'])): ?>
                            <span class="badge badge-jellyfin">Jellyfin Boxset</span>
                        <?php else: ?>
                            <span class="badge badge-custom">Custom</span>
                        <?php endif; ?>
                    </td>
                    <td style="text-align:center;"><?php echo intval($col['item_count']); ?></td>
                    <td>
                        <div class="actions">
                            <a href="collection_edit.php?id=<?php echo $col['id']; ?>" class="btn btn-secondary btn-sm">Edit</a>
                            <button class="btn btn-sm" onclick="verifyCollection(<?php echo $col['id']; ?>, this)">Verify</button>
                            <form method="POST" style="display:inline;"
                                  onsubmit="return confirm('Delete collection \'<?php echo addslashes(htmlspecialchars($col['name'])); ?>\'?');">
                                <input type="hidden" name="action" value="delete">
                                <input type="hidden" name="collection_id" value="<?php echo $col['id']; ?>">
                                <button type="submit" class="btn btn-danger btn-sm">Delete</button>
                            </form>
                        </div>
                        <div id="verify-<?php echo $col['id']; ?>" class="verify-results"></div>
                    </td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
        <?php endif; ?>
    </div>
</div>

<!-- Import Boxset Modal -->
<div class="modal-overlay" id="import-modal">
    <div class="modal">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
            <h2 style="margin:0;">Import Jellyfin Boxset</h2>
            <button onclick="closeImportModal()" style="background:none;border:none;color:#888;font-size:20px;cursor:pointer;">✕</button>
        </div>
        <div id="boxset-loading" style="color:#888;font-size:14px;">Loading boxsets…</div>
        <ul class="boxset-list" id="boxset-list"></ul>
    </div>
</div>

<script>
const API_BASE = '<?php echo getClientApiBaseUrl(); ?>';

function showStatus(msg, ok) {
    const el = document.getElementById('status-msg');
    el.textContent = msg;
    el.className = ok ? 'status-ok' : 'status-err';
    el.style.display = 'block';
}

// ─── Verify ────────────────────────────────────────────────────────────────
async function verifyCollection(collectionId, btn) {
    const container = document.getElementById('verify-' + collectionId);
    container.innerHTML = '<span style="color:#888;font-size:12px;">Checking…</span>';
    btn.disabled = true;
    try {
        const resp = await fetch(`${API_BASE}/collections/${collectionId}/verify`);
        const data = await resp.json();
        if (!resp.ok) { container.innerHTML = `<span class="v-deleted">${data.detail}</span>`; return; }
        const s = data.summary;
        let html = `<small>`;
        if (s.ok)      html += `<span class="v-ok">✓ ${s.ok} ok</span> `;
        if (s.moved)   html += `<span class="v-moved">⚠ ${s.moved} moved</span> `;
        if (s.deleted) html += `<span class="v-deleted">✗ ${s.deleted} deleted</span> `;
        if (s.no_path) html += `<span class="v-nopath">? ${s.no_path} no path</span>`;
        html += `</small>`;
        if (s.deleted > 0 || s.moved > 0) {
            html += `<br><small><a href="collection_edit.php?id=${collectionId}&verify=1" style="color:#00A4DC;">View details →</a></small>`;
        }
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = `<span class="v-deleted">Error: ${e.message}</span>`;
    } finally {
        btn.disabled = false;
    }
}

// ─── Import Boxset Modal ───────────────────────────────────────────────────
async function openImportModal() {
    document.getElementById('import-modal').classList.add('open');
    const loading = document.getElementById('boxset-loading');
    const list    = document.getElementById('boxset-list');
    loading.style.display = 'block';
    list.innerHTML = '';
    try {
        const resp = await fetch(`${API_BASE}/jellyfin/boxsets`);
        const data = await resp.json();
        loading.style.display = 'none';
        const boxsets = data.boxsets || [];
        if (boxsets.length === 0) {
            loading.textContent = 'No Jellyfin boxsets found.';
            loading.style.display = 'block';
            return;
        }
        for (const bs of boxsets) {
            const li = document.createElement('li');
            li.innerHTML = `
                <span class="boxset-name">${esc(bs.Name)}</span>
                <button class="btn btn-sm btn-primary" onclick="importBoxset('${esc(bs.Id)}', '${esc(bs.Name)}', this)">Import</button>
            `;
            list.appendChild(li);
        }
    } catch (e) {
        loading.textContent = 'Failed to load boxsets: ' + e.message;
    }
}

function closeImportModal() {
    document.getElementById('import-modal').classList.remove('open');
}

async function importBoxset(id, name, btn) {
    btn.disabled = true;
    btn.textContent = 'Importing…';
    try {
        const resp = await fetch(`${API_BASE}/collections/import/${encodeURIComponent(id)}`, { method: 'POST' });
        const data = await resp.json();
        closeImportModal();
        if (resp.ok) {
            showStatus(data.message || 'Imported!', true);
            setTimeout(() => location.reload(), 1200);
        } else {
            showStatus(data.detail || 'Import failed', false);
        }
    } catch (e) {
        showStatus('Network error: ' + e.message, false);
        btn.disabled = false;
        btn.textContent = 'Import';
    }
}

// Close modal when clicking outside
document.getElementById('import-modal').addEventListener('click', function(e) {
    if (e.target === this) closeImportModal();
});

function esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
</script>
</body>
</html>
