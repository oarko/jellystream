<?php
require_once '../config/config.php';
require_once '../includes/api_client.php';

$api = new ApiClient();

$channel_id = isset($_GET['id']) ? intval($_GET['id']) : null;
$is_edit    = $channel_id !== null;

// Load existing channel data when editing
$channel = null;
if ($is_edit) {
    $resp = $api->getChannel($channel_id);
    if ($resp['success']) {
        $channel = $resp['data'];
    } else {
        die('Channel not found');
    }
}

// Load Jellyfin libraries for the picker
$lib_resp  = $api->getJellyfinLibraries();
$jf_libraries = ($lib_resp['success'] && isset($lib_resp['data']['libraries']))
    ? $lib_resp['data']['libraries']
    : [];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo $is_edit ? 'Edit' : 'Create'; ?> Channel - <?php echo APP_NAME; ?></title>
    <link rel="stylesheet" href="/static/css/style.css">
    <style>
        body { font-family: Arial, sans-serif; background: #181818; color: #fff; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .card { background: #1F1F1F; border-radius: 8px; padding: 24px; margin-bottom: 20px; }
        h1 { color: #00A4DC; margin: 0 0 4px; }
        h2 { color: #ccc; font-size: 16px; margin: 0 0 16px; border-bottom: 1px solid #333; padding-bottom: 8px; }
        .form-group { margin-bottom: 16px; }
        label { display: block; margin-bottom: 6px; color: #aaa; font-size: 14px; }
        input[type=text], input[type=number], select, textarea {
            width: 100%; padding: 9px 12px; background: #2a2a2a; border: 1px solid #444;
            border-radius: 4px; color: #fff; font-size: 14px; box-sizing: border-box;
        }
        input[type=text]:focus, select:focus { outline: none; border-color: #00A4DC; }
        .toggle-row { display: flex; align-items: center; gap: 12px; }
        .toggle-row label { margin: 0; color: #ccc; }
        .switch { position: relative; display: inline-block; width: 44px; height: 24px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; inset: 0; background: #444; border-radius: 24px; transition: .3s; }
        .slider:before { position: absolute; content:""; height:18px; width:18px; left:3px; bottom:3px; background:#fff; border-radius:50%; transition:.3s; }
        input:checked + .slider { background: #00A4DC; }
        input:checked + .slider:before { transform: translateX(20px); }

        /* Library list */
        .lib-list { list-style: none; margin: 0; padding: 0; }
        .lib-item { display: flex; align-items: center; gap: 10px; background: #2a2a2a; border-radius: 6px; padding: 8px 12px; margin-bottom: 8px; }
        .lib-item .lib-name { flex: 1; font-size: 14px; }
        .lib-item .lib-type { font-size: 12px; color: #888; }
        .lib-item button { background: #c0392b; border: none; color: #fff; border-radius: 4px; padding: 4px 10px; cursor: pointer; font-size: 12px; }
        .add-row { display: flex; gap: 8px; align-items: center; margin-top: 8px; }
        .add-row select { flex: 1; }
        .add-row button { background: #00A4DC; border: none; color: #fff; border-radius: 4px; padding: 8px 14px; cursor: pointer; white-space: nowrap; }

        /* Genre filters */
        .genre-list { list-style: none; margin: 0; padding: 0; }
        .genre-item { display: flex; align-items: center; gap: 10px; background: #2a2a2a; border-radius: 6px; padding: 8px 12px; margin-bottom: 8px; }
        .genre-item .genre-name { flex: 1; font-size: 14px; }
        .genre-item .genre-ct { font-size: 12px; color: #888; }
        .genre-item button { background: #c0392b; border: none; color: #fff; border-radius: 4px; padding: 4px 10px; cursor: pointer; font-size: 12px; }
        .genre-add-row { display: flex; gap: 8px; align-items: center; margin-top: 8px; }
        .genre-add-row input { flex: 2; }
        .genre-add-row select { flex: 1; }
        .genre-add-row button { background: #00A4DC; border: none; color: #fff; border-radius: 4px; padding: 8px 14px; cursor: pointer; white-space: nowrap; }

        .form-actions { display: flex; gap: 12px; justify-content: flex-end; margin-top: 8px; }
        .btn { padding: 10px 22px; border-radius: 4px; border: none; cursor: pointer; font-size: 14px; text-decoration: none; display: inline-block; }
        .btn-primary { background: #00A4DC; color: #fff; }
        .btn-secondary { background: #444; color: #fff; }
        #status-msg { margin-top: 16px; padding: 12px; border-radius: 6px; display: none; font-size: 14px; }
        .status-ok  { background: #1b5e20; color: #a5d6a7; }
        .status-err { background: #7f0000; color: #ef9a9a; }
        .hint { font-size: 12px; color: #666; margin-top: 4px; }
        #genre-section { display: none; }
    </style>
</head>
<body>
<div class="container">
    <div class="card">
        <h1><?php echo $is_edit ? 'Edit Channel' : 'Create Channel'; ?></h1>
        <p style="color:#888;margin:0 0 24px;">
            <?php echo $is_edit ? "Editing channel: <strong>{$channel['name']}</strong>" : 'Configure a new 24/7 virtual TV channel.'; ?>
        </p>

        <!-- Basic Info -->
        <h2>Basic Info</h2>
        <div class="form-group">
            <label>Channel Name *</label>
            <input type="text" id="ch-name" value="<?php echo htmlspecialchars($channel['name'] ?? ''); ?>" placeholder="e.g. Sci-Fi All Night">
        </div>
        <div class="form-group">
            <label>Description</label>
            <input type="text" id="ch-desc" value="<?php echo htmlspecialchars($channel['description'] ?? ''); ?>" placeholder="Optional description">
        </div>
        <div class="form-group">
            <label>Channel Number</label>
            <input type="text" id="ch-num" value="<?php echo htmlspecialchars($channel['channel_number'] ?? ''); ?>" placeholder="e.g. 101.1">
            <div class="hint">Leave blank to auto-assign.</div>
        </div>
        <div class="form-group toggle-row">
            <label class="switch">
                <input type="checkbox" id="ch-enabled" <?php echo (!$is_edit || ($channel['enabled'] ?? true)) ? 'checked' : ''; ?>>
                <span class="slider"></span>
            </label>
            <label for="ch-enabled">Channel enabled</label>
        </div>

        <!-- Schedule Type -->
        <h2 style="margin-top:24px;">Schedule Type</h2>
        <div class="form-group">
            <label>Mode</label>
            <select id="ch-schedule-type" onchange="toggleGenreSection()">
                <option value="genre_auto" <?php echo (!$is_edit || ($channel['schedule_type'] ?? '') === 'genre_auto') ? 'selected' : ''; ?>>
                    Auto (Genre-based, 24/7 continuous)
                </option>
                <option value="manual" <?php echo ($is_edit && ($channel['schedule_type'] ?? '') === 'manual') ? 'selected' : ''; ?>>
                    Manual (schedule entries via API)
                </option>
            </select>
            <div class="hint">Auto mode generates a 7-day schedule from genre-matching items and keeps it topped up daily.</div>
        </div>

        <!-- Libraries -->
        <h2 style="margin-top:24px;">Libraries</h2>
        <div class="hint" style="margin-bottom:12px;">Add one or more Jellyfin libraries to source content from.</div>
        <ul class="lib-list" id="lib-list">
            <?php foreach (($channel['libraries'] ?? []) as $lib): ?>
            <li class="lib-item"
                data-id="<?php echo htmlspecialchars($lib['library_id']); ?>"
                data-name="<?php echo htmlspecialchars($lib['library_name']); ?>"
                data-type="<?php echo htmlspecialchars($lib['collection_type']); ?>">
                <span class="lib-name"><?php echo htmlspecialchars($lib['library_name']); ?></span>
                <span class="lib-type"><?php echo htmlspecialchars($lib['collection_type']); ?></span>
                <button onclick="removeLib(this)">✕</button>
            </li>
            <?php endforeach; ?>
        </ul>
        <div class="add-row">
            <select id="lib-picker">
                <option value="">— Select a library —</option>
                <?php foreach ($jf_libraries as $jl): ?>
                <option
                    value="<?php echo htmlspecialchars($jl['Id']); ?>"
                    data-name="<?php echo htmlspecialchars($jl['Name']); ?>"
                    data-type="<?php echo htmlspecialchars(strtolower($jl['CollectionType'] ?? 'mixed')); ?>">
                    <?php echo htmlspecialchars($jl['Name']); ?>
                    (<?php echo htmlspecialchars($jl['CollectionType'] ?? 'mixed'); ?>)
                </option>
                <?php endforeach; ?>
            </select>
            <button onclick="addLib()">+ Add Library</button>
        </div>

        <!-- Genre Filters -->
        <div id="genre-section">
            <h2 style="margin-top:24px;">Genre Filters</h2>
            <div class="hint" style="margin-bottom:12px;">
                Restrict content to these genres. Leave empty to include all genres from the selected libraries.
            </div>
            <ul class="genre-list" id="genre-list">
                <?php foreach (($channel['genre_filters'] ?? []) as $gf): ?>
                <li class="genre-item"
                    data-genre="<?php echo htmlspecialchars($gf['genre']); ?>"
                    data-ct="<?php echo htmlspecialchars($gf['content_type']); ?>">
                    <span class="genre-name"><?php echo htmlspecialchars($gf['genre']); ?></span>
                    <span class="genre-ct"><?php echo htmlspecialchars($gf['content_type']); ?></span>
                    <button onclick="removeGenre(this)">✕</button>
                </li>
                <?php endforeach; ?>
            </ul>
            <div class="genre-add-row">
                <input type="text" id="genre-input" placeholder="Genre name (e.g. Sci-Fi)">
                <select id="genre-ct">
                    <option value="both">Movies + Episodes</option>
                    <option value="movie">Movies only</option>
                    <option value="episode">Episodes only</option>
                </select>
                <button onclick="addGenre()">+ Add Genre</button>
            </div>
        </div>

        <!-- Actions -->
        <div class="form-actions">
            <a href="channels.php" class="btn btn-secondary">Cancel</a>
            <button class="btn btn-primary" onclick="saveChannel()">
                <?php echo $is_edit ? 'Save Changes' : 'Create Channel'; ?>
            </button>
        </div>
        <div id="status-msg"></div>
    </div>
</div>

<script>
const IS_EDIT    = <?php echo $is_edit ? 'true' : 'false'; ?>;
const CHANNEL_ID = <?php echo $channel_id ?? 'null'; ?>;
const API_BASE   = '<?php echo getApiBaseUrl(); ?>';

function toggleGenreSection() {
    const mode = document.getElementById('ch-schedule-type').value;
    document.getElementById('genre-section').style.display = mode === 'genre_auto' ? 'block' : 'none';
}
toggleGenreSection();

// ── Library helpers ───────────────────────────────────────────────────────────
function addLib() {
    const picker = document.getElementById('lib-picker');
    const opt    = picker.options[picker.selectedIndex];
    if (!opt.value) return;

    const id   = opt.value;
    const name = opt.dataset.name;
    const type = opt.dataset.type;

    // Prevent duplicates
    const existing = document.querySelectorAll('#lib-list li');
    for (const li of existing) {
        if (li.dataset.id === id) { alert('Library already added.'); return; }
    }

    const li = document.createElement('li');
    li.className = 'lib-item';
    li.dataset.id   = id;
    li.dataset.name = name;
    li.dataset.type = type;
    li.innerHTML = `<span class="lib-name">${esc(name)}</span><span class="lib-type">${esc(type)}</span><button onclick="removeLib(this)">✕</button>`;
    document.getElementById('lib-list').appendChild(li);
    picker.selectedIndex = 0;
}

function removeLib(btn) { btn.closest('li').remove(); }

function getLibraries() {
    return [...document.querySelectorAll('#lib-list li')].map(li => ({
        library_id:      li.dataset.id,
        library_name:    li.dataset.name,
        collection_type: li.dataset.type,
    }));
}

// ── Genre helpers ─────────────────────────────────────────────────────────────
function addGenre() {
    const input = document.getElementById('genre-input');
    const ct    = document.getElementById('genre-ct');
    const genre = input.value.trim();
    if (!genre) { alert('Enter a genre name.'); return; }

    const li = document.createElement('li');
    li.className = 'genre-item';
    li.dataset.genre = genre;
    li.dataset.ct    = ct.value;
    li.innerHTML = `<span class="genre-name">${esc(genre)}</span><span class="genre-ct">${esc(ct.value)}</span><button onclick="removeGenre(this)">✕</button>`;
    document.getElementById('genre-list').appendChild(li);
    input.value = '';
    ct.selectedIndex = 0;
}

function removeGenre(btn) { btn.closest('li').remove(); }

function getGenreFilters() {
    return [...document.querySelectorAll('#genre-list li')].map(li => ({
        genre:        li.dataset.genre,
        content_type: li.dataset.ct,
    }));
}

// ── Save ──────────────────────────────────────────────────────────────────────
async function saveChannel() {
    const name = document.getElementById('ch-name').value.trim();
    if (!name) { showStatus('Channel name is required.', false); return; }

    const libs = getLibraries();
    if (!libs.length) { showStatus('Add at least one library.', false); return; }

    const payload = {
        name:          name,
        description:   document.getElementById('ch-desc').value.trim() || null,
        channel_number: document.getElementById('ch-num').value.trim() || null,
        enabled:       document.getElementById('ch-enabled').checked,
        schedule_type: document.getElementById('ch-schedule-type').value,
        libraries:     libs,
        genre_filters: getGenreFilters(),
    };

    const url    = IS_EDIT ? `${API_BASE}/channels/${CHANNEL_ID}` : `${API_BASE}/channels/`;
    const method = IS_EDIT ? 'PUT' : 'POST';

    try {
        const resp = await fetch(url, {
            method:  method,
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(payload),
        });
        const data = await resp.json();
        if (resp.ok) {
            showStatus(data.message || 'Saved!', true);
            setTimeout(() => { window.location.href = 'channels.php'; }, 1200);
        } else {
            showStatus(data.detail || JSON.stringify(data), false);
        }
    } catch (e) {
        showStatus('Network error: ' + e.message, false);
    }
}

function showStatus(msg, ok) {
    const el = document.getElementById('status-msg');
    el.textContent = msg;
    el.className   = ok ? 'status-ok' : 'status-err';
    el.style.display = 'block';
}

function esc(s) {
    return String(s)
        .replace(/&/g,'&amp;').replace(/</g,'&lt;')
        .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
</script>
</body>
</html>
