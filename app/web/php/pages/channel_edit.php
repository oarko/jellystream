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

// Pre-fill JellyStream public URL from health endpoint (JELLYSTREAM_PUBLIC_URL setting)
// Falls back to the browser hostname if not configured.
$health_resp = $api->healthCheck();
$configured_public_url = $health_resp['data']['public_url'] ?? null;
if ($configured_public_url) {
    $public_url_default = $configured_public_url;
} else {
    $hostname = strtok($_SERVER['HTTP_HOST'] ?? 'localhost', ':');
    $public_url_default = "http://{$hostname}:8000";
}
$public_url_is_local = in_array(
    parse_url($public_url_default, PHP_URL_HOST),
    ['localhost', '127.0.0.1', '::1']
);
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
        .genre-item .genre-ft { font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 10px; flex-shrink: 0; }
        .genre-item .genre-ft.ft-include { background: #1b5e20; color: #a5d6a7; }
        .genre-item .genre-ft.ft-exclude { background: #7f0000; color: #ef9a9a; }
        .genre-item .genre-name { flex: 1; font-size: 14px; }
        .genre-item .genre-ct { font-size: 12px; color: #888; }
        .genre-item button { background: #c0392b; border: none; color: #fff; border-radius: 4px; padding: 4px 10px; cursor: pointer; font-size: 12px; }
        .genre-add-row { display: flex; gap: 8px; align-items: center; margin-top: 8px; flex-wrap: wrap; }
        .genre-add-row select { flex: 2; min-width: 120px; }
        .genre-add-row select.ct-select { flex: 1; min-width: 100px; }
        .genre-add-row select.ft-select { flex: 1; min-width: 100px; }
        .genre-add-row button { background: #00A4DC; border: none; color: #fff; border-radius: 4px; padding: 8px 14px; cursor: pointer; white-space: nowrap; }
        .genre-loading { font-size: 12px; color: #888; margin-top: 4px; min-height: 16px; }

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

        <!-- Channel Type -->
        <h2 style="margin-top:24px;">Channel Type</h2>
        <div class="form-group">
            <label>Type</label>
            <select id="ch-type" onchange="onTypeChange()">
                <option value="video" <?php echo (!$is_edit || ($channel['channel_type'] ?? 'video') === 'video') ? 'selected' : ''; ?>>
                    Video (Movies &amp; TV Shows)
                </option>
                <option value="music" disabled <?php echo ($is_edit && ($channel['channel_type'] ?? '') === 'music') ? 'selected' : ''; ?>>
                    Music (coming soon)
                </option>
            </select>
            <div class="hint">Video channels pull from Movies and TV Shows libraries.</div>
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
                <?php foreach (($channel['genre_filters'] ?? []) as $gf):
                    $ft = htmlspecialchars($gf['filter_type'] ?? 'include');
                    $ft_label = ($gf['filter_type'] ?? 'include') === 'exclude' ? 'Exclude' : 'Include';
                    $ft_class = ($gf['filter_type'] ?? 'include') === 'exclude' ? 'ft-exclude' : 'ft-include';
                ?>
                <li class="genre-item"
                    data-genre="<?php echo htmlspecialchars($gf['genre']); ?>"
                    data-ct="<?php echo htmlspecialchars($gf['content_type']); ?>"
                    data-filter-type="<?php echo $ft; ?>">
                    <span class="genre-ft <?php echo $ft_class; ?>"><?php echo $ft_label; ?></span>
                    <span class="genre-name"><?php echo htmlspecialchars($gf['genre']); ?></span>
                    <span class="genre-ct"><?php echo htmlspecialchars($gf['content_type']); ?></span>
                    <button onclick="removeGenre(this)">✕</button>
                </li>
                <?php endforeach; ?>
            </ul>
            <div class="genre-add-row">
                <select id="genre-select">
                    <option value="">— Add a library first —</option>
                </select>
                <select id="genre-ct" class="ct-select">
                    <option value="both">Movies + Episodes</option>
                    <option value="movie">Movies only</option>
                    <option value="episode">Episodes only</option>
                </select>
                <select id="genre-filter-type" class="ft-select">
                    <option value="include">Include</option>
                    <option value="exclude">Exclude</option>
                </select>
                <button onclick="addGenre()">+ Add Genre</button>
            </div>
            <div class="genre-loading" id="genre-loading"></div>
        </div>

        <?php if ($is_edit): ?>
        <!-- Schedule actions -->
        <div style="margin-top:24px;border-top:1px solid #333;padding-top:16px;">
            <h2>Schedule</h2>
            <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
                <button class="btn btn-secondary" onclick="regenerateSchedule()" id="regen-btn">
                    ↺ Regenerate Schedule (7 days)
                </button>
                <span id="regen-status" style="font-size:13px;color:#888;"></span>
            </div>
            <div class="hint" style="margin-top:8px;">
                Clears and rebuilds the schedule from scratch using the current library and genre settings.
                Run this after changing libraries or genre filters.
            </div>
        </div>
        <?php endif; ?>

        <!-- Actions -->
        <div class="form-actions">
            <a href="channels.php" class="btn btn-secondary">Cancel</a>
            <?php if ($is_edit): ?>
            <button class="btn" style="background:#c0392b;color:#fff;" onclick="deleteChannel()">Delete Channel</button>
            <?php endif; ?>
            <button class="btn btn-primary" onclick="saveChannel()">
                <?php echo $is_edit ? 'Save Changes' : 'Create Channel'; ?>
            </button>
        </div>
        <div id="status-msg"></div>
    </div>

<?php if ($is_edit): ?>
    <!-- Jellyfin Live TV Registration -->
    <div class="card" id="livetv-card">
        <h2>Jellyfin Live TV Registration</h2>

        <?php
        $registered = !empty($channel['tuner_host_id']) || !empty($channel['listing_provider_id']);
        ?>

        <div id="livetv-status" style="margin-bottom:16px;">
            <?php if ($registered): ?>
                <div style="background:#1b5e20;color:#a5d6a7;padding:10px 14px;border-radius:6px;font-size:13px;">
                    ✅ Registered with Jellyfin Live TV<br>
                    <small style="opacity:.8;">
                        Tuner ID: <?php echo htmlspecialchars($channel['tuner_host_id'] ?? '—'); ?> &nbsp;|&nbsp;
                        EPG ID: <?php echo htmlspecialchars($channel['listing_provider_id'] ?? '—'); ?>
                    </small>
                </div>
            <?php else: ?>
                <div style="background:#2a2a2a;color:#888;padding:10px 14px;border-radius:6px;font-size:13px;">
                    Not registered — fill in the form below to add this channel to Jellyfin Live TV.
                </div>
            <?php endif; ?>
        </div>

        <?php if (!$registered): ?>
        <!-- Registration form (only shown when not yet registered) -->
        <div id="reg-form">
            <?php if ($public_url_is_local): ?>
            <div style="background:#7f2700;color:#ffccbc;padding:10px 14px;border-radius:6px;font-size:13px;margin-bottom:14px;">
                ⚠️ The pre-filled URL uses <strong>localhost</strong>. Jellyfin cannot reach JellyStream via
                <code>localhost</code> — it will try to connect to its own machine. Enter the network IP of
                this JellyStream server (e.g. <code>http://10.12.1.134:8000</code>).<br>
                <small style="opacity:.8;">
                    Set <code>JELLYSTREAM_PUBLIC_URL=http://&lt;your-ip&gt;:8000</code> in your <code>.env</code>
                    to avoid seeing this warning.
                </small>
            </div>
            <?php endif; ?>
            <div class="form-group">
                <label>JellyStream Public URL <span style="color:#c0392b;">*</span></label>
                <input type="text" id="reg-public-url"
                    placeholder="http://192.168.1.100:8000"
                    value="<?php echo htmlspecialchars($public_url_default); ?>">
                <div class="hint">
                    The URL Jellyfin uses to reach JellyStream. Must be the machine's network IP,
                    not localhost. Registers a single global tuner — all channels are included automatically.
                </div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                <div class="form-group">
                    <label>Tuner Count</label>
                    <input type="number" id="reg-tuner-count" value="1" min="0" max="32">
                    <div class="hint">Max simultaneous streams. 0 = unlimited.</div>
                </div>
                <div class="form-group">
                    <label>Fallback Max Bitrate (bps)</label>
                    <input type="number" id="reg-max-bitrate" value="0" min="0">
                    <div class="hint">0 = no limit.</div>
                </div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:16px;">
                <div class="toggle-row">
                    <label class="switch">
                        <input type="checkbox" id="reg-hw-transcode">
                        <span class="slider"></span>
                    </label>
                    <label for="reg-hw-transcode" style="font-size:13px;">HW Transcoding</label>
                </div>
                <div class="toggle-row">
                    <label class="switch">
                        <input type="checkbox" id="reg-fmp4" >
                        <span class="slider"></span>
                    </label>
                    <label for="reg-fmp4" style="font-size:13px;">fMP4 Container</label>
                </div>
                <div class="toggle-row">
                    <label class="switch">
                        <input type="checkbox" id="reg-stream-loop" checked>
                        <span class="slider"></span>
                    </label>
                    <label for="reg-stream-loop" style="font-size:13px;">Stream Looping</label>
                </div>
                <div class="toggle-row">
                    <label class="switch">
                        <input type="checkbox" id="reg-stream-sharing" checked>
                        <span class="slider"></span>
                    </label>
                    <label for="reg-stream-sharing" style="font-size:13px;">Stream Sharing</label>
                </div>
                <div class="toggle-row">
                    <label class="switch">
                        <input type="checkbox" id="reg-ignore-dts">
                        <span class="slider"></span>
                    </label>
                    <label for="reg-ignore-dts" style="font-size:13px;">Ignore DTS</label>
                </div>
                <div class="toggle-row">
                    <label class="switch">
                        <input type="checkbox" id="reg-native-framerate">
                        <span class="slider"></span>
                    </label>
                    <label for="reg-native-framerate" style="font-size:13px;">Native Framerate</label>
                </div>
            </div>

            <button class="btn btn-primary" onclick="registerLiveTV()">Register with Jellyfin Live TV</button>
        </div>
        <?php else: ?>
        <!-- Unregister option when already registered -->
        <button class="btn btn-danger" onclick="unregisterLiveTV()" style="background:#c0392b;border:none;color:#fff;padding:10px 20px;border-radius:4px;cursor:pointer;">
            Unregister from Jellyfin Live TV
        </button>
        <?php endif; ?>

        <div id="livetv-msg" style="margin-top:14px;display:none;padding:10px 14px;border-radius:6px;font-size:13px;"></div>
    </div>
<?php endif; ?>

</div>

<script>
const IS_EDIT    = <?php echo $is_edit ? 'true' : 'false'; ?>;
const CHANNEL_ID = <?php echo $channel_id ?? 'null'; ?>;
const API_BASE   = '<?php echo getClientApiBaseUrl(); ?>';

// ── Channel type ──────────────────────────────────────────────────────────────
// CollectionTypes valid for Video channels
const VIDEO_TYPES = new Set(['movies', 'tvshows']);

function onTypeChange() {
    filterLibraryPicker();
}

function filterLibraryPicker() {
    const type = document.getElementById('ch-type').value;
    const picker = document.getElementById('lib-picker');
    for (const opt of picker.options) {
        if (!opt.value) continue; // keep placeholder
        const ct = opt.dataset.type || '';
        if (type === 'video') {
            opt.hidden = !VIDEO_TYPES.has(ct);
        } else {
            opt.hidden = false;
        }
    }
    // Reset selection if current is now hidden
    const sel = picker.options[picker.selectedIndex];
    if (sel && sel.hidden) picker.selectedIndex = 0;
}

// ── Genre dropdown pool ────────────────────────────────────────────────────────
// Maps library_id → Set of genre strings fetched from the API
const genrePool = {};

async function fetchLibraryGenres(libraryId) {
    const loading = document.getElementById('genre-loading');
    loading.textContent = 'Loading genres…';
    try {
        const resp = await fetch(`${API_BASE}/jellyfin/genres/${encodeURIComponent(libraryId)}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        genrePool[libraryId] = new Set(data.genres || []);
        loading.textContent = '';
    } catch (e) {
        loading.textContent = `Could not load genres: ${e.message}`;
        genrePool[libraryId] = new Set();
    }
    refreshGenreDropdown();
}

function refreshGenreDropdown() {
    // Merge all genres from all libraries in the pool
    const all = new Set();
    for (const genres of Object.values(genrePool)) {
        for (const g of genres) all.add(g);
    }
    const sorted = [...all].sort((a, b) => a.localeCompare(b));

    // Collect already-added genres so we can mark them
    const added = new Set(
        [...document.querySelectorAll('#genre-list li')].map(li => li.dataset.genre)
    );

    const sel = document.getElementById('genre-select');
    const prev = sel.value;
    sel.innerHTML = '';

    if (sorted.length === 0) {
        const ph = document.createElement('option');
        ph.value = '';
        ph.textContent = Object.keys(genrePool).length === 0
            ? '— Add a library first —'
            : '— No genres found —';
        sel.appendChild(ph);
    } else {
        const ph = document.createElement('option');
        ph.value = '';
        ph.textContent = '— Select a genre —';
        sel.appendChild(ph);

        for (const g of sorted) {
            const opt = document.createElement('option');
            opt.value = g;
            opt.textContent = added.has(g) ? `${g} ✓` : g;
            if (added.has(g)) opt.style.color = '#888';
            sel.appendChild(opt);
        }
        // Restore previous selection if still valid
        if (prev && sorted.includes(prev)) sel.value = prev;
    }
}

function toggleGenreSection() {
    const mode = document.getElementById('ch-schedule-type').value;
    document.getElementById('genre-section').style.display = mode === 'genre_auto' ? 'block' : 'none';
}
toggleGenreSection();

// ── Library helpers ───────────────────────────────────────────────────────────
async function addLib() {
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

    // Fetch genres for this library and add to the pool
    await fetchLibraryGenres(id);
}

function removeLib(btn) {
    const li = btn.closest('li');
    const id = li.dataset.id;
    li.remove();

    // Remove this library's genres from the pool and refresh dropdown
    delete genrePool[id];
    refreshGenreDropdown();
}

function getLibraries() {
    return [...document.querySelectorAll('#lib-list li')].map(li => ({
        library_id:      li.dataset.id,
        library_name:    li.dataset.name,
        collection_type: li.dataset.type,
    }));
}

// ── Genre helpers ─────────────────────────────────────────────────────────────
function addGenre() {
    const sel = document.getElementById('genre-select');
    const ct  = document.getElementById('genre-ct');
    const ft  = document.getElementById('genre-filter-type');
    const genre = sel.value;
    if (!genre) { alert('Select a genre from the dropdown.'); return; }

    // Prevent duplicates
    const existing = document.querySelectorAll('#genre-list li');
    for (const li of existing) {
        if (li.dataset.genre === genre) { alert('Genre already added.'); return; }
    }

    const ftVal   = ft.value;
    const ftLabel = ftVal === 'exclude' ? 'Exclude' : 'Include';
    const ftClass = ftVal === 'exclude' ? 'ft-exclude' : 'ft-include';

    const li = document.createElement('li');
    li.className = 'genre-item';
    li.dataset.genre      = genre;
    li.dataset.ct         = ct.value;
    li.dataset.filterType = ftVal;
    li.innerHTML = `<span class="genre-ft ${ftClass}">${ftLabel}</span><span class="genre-name">${esc(genre)}</span><span class="genre-ct">${esc(ct.value)}</span><button onclick="removeGenre(this)">✕</button>`;
    document.getElementById('genre-list').appendChild(li);
    sel.value = '';
    ct.selectedIndex = 0;
    ft.selectedIndex = 0;

    // Refresh dropdown to show checkmark on added genre
    refreshGenreDropdown();
}

function removeGenre(btn) {
    btn.closest('li').remove();
    // Refresh to un-mark the genre in the dropdown
    refreshGenreDropdown();
}

function getGenreFilters() {
    return [...document.querySelectorAll('#genre-list li')].map(li => ({
        genre:        li.dataset.genre,
        content_type: li.dataset.ct,
        filter_type:  li.dataset.filterType || 'include',
    }));
}

// ── Regenerate Schedule ───────────────────────────────────────────────────────
async function regenerateSchedule() {
    const btn = document.getElementById('regen-btn');
    const status = document.getElementById('regen-status');
    btn.disabled = true;
    status.style.color = '#888';
    status.textContent = 'Generating…';

    try {
        const resp = await fetch(`<?php echo API_BASE_URL; ?>/channels/<?php echo (int)$channel_id; ?>/generate-schedule?days=7&reset=true`, {
            method: 'POST',
        });
        const data = await resp.json();
        if (resp.ok) {
            status.style.color = '#27ae60';
            status.textContent = `✓ ${data.count ?? 0} schedule entries created.`;
        } else {
            status.style.color = '#e74c3c';
            status.textContent = `Error: ${data.detail ?? resp.status}`;
        }
    } catch (e) {
        status.style.color = '#e74c3c';
        status.textContent = 'Request failed — is the API running?';
    } finally {
        btn.disabled = false;
    }
}

// ── Save ──────────────────────────────────────────────────────────────────────
async function saveChannel() {
    const name = document.getElementById('ch-name').value.trim();
    if (!name) { showStatus('Channel name is required.', false); return; }

    const libs = getLibraries();
    if (!libs.length) { showStatus('Add at least one library.', false); return; }

    const payload = {
        name:           name,
        description:    document.getElementById('ch-desc').value.trim() || null,
        channel_number: document.getElementById('ch-num').value.trim() || null,
        enabled:        document.getElementById('ch-enabled').checked,
        channel_type:   document.getElementById('ch-type').value,
        schedule_type:  document.getElementById('ch-schedule-type').value,
        libraries:      libs,
        genre_filters:  getGenreFilters(),
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

// ── Delete ────────────────────────────────────────────────────────────────────
async function deleteChannel() {
    const name = document.getElementById('ch-name').value.trim() || 'this channel';
    if (!confirm(`Delete "${name}"?\n\nThis will permanently remove the channel and all its schedule entries. This cannot be undone.`)) return;

    try {
        const resp = await fetch(`${API_BASE}/channels/${CHANNEL_ID}`, { method: 'DELETE' });
        const data = await resp.json();
        if (resp.ok) {
            window.location.href = 'channels.php';
        } else {
            showStatus(data.detail || 'Delete failed.', false);
        }
    } catch (e) {
        showStatus('Network error: ' + e.message, false);
    }
}

// ── Live TV Registration ───────────────────────────────────────────────────────
async function registerLiveTV() {
    const publicUrl = document.getElementById('reg-public-url')?.value.trim();
    if (!publicUrl) { showLiveTVMsg('Public URL is required.', false); return; }

    const payload = {
        public_url:               publicUrl,
        tuner_count:              parseInt(document.getElementById('reg-tuner-count').value) || 1,
        fallback_max_bitrate:     parseInt(document.getElementById('reg-max-bitrate').value) || 0,
        allow_hw_transcoding:     document.getElementById('reg-hw-transcode').checked,
        allow_fmp4_transcoding:   document.getElementById('reg-fmp4').checked,
        enable_stream_looping:    document.getElementById('reg-stream-loop').checked,
        allow_stream_sharing:     document.getElementById('reg-stream-sharing').checked,
        ignore_dts:               document.getElementById('reg-ignore-dts').checked,
        read_at_native_framerate: document.getElementById('reg-native-framerate').checked,
    };

    showLiveTVMsg('Registering…', true);
    try {
        const resp = await fetch(`${API_BASE}/channels/${CHANNEL_ID}/register-livetv`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(payload),
        });
        const data = await resp.json();
        if (resp.ok) {
            showLiveTVMsg(
                `Registered! Tuner ID: ${data.tuner_host_id} | EPG ID: ${data.listing_provider_id}`,
                true
            );
            setTimeout(() => location.reload(), 1800);
        } else {
            showLiveTVMsg(data.detail || JSON.stringify(data), false);
        }
    } catch (e) {
        showLiveTVMsg('Network error: ' + e.message, false);
    }
}

async function unregisterLiveTV() {
    if (!confirm('Remove this channel from Jellyfin Live TV?')) return;

    showLiveTVMsg('Unregistering…', true);
    try {
        const resp = await fetch(`${API_BASE}/channels/${CHANNEL_ID}/register-livetv`, {
            method: 'DELETE',
        });
        const data = await resp.json();
        if (resp.ok) {
            showLiveTVMsg(data.message || 'Unregistered.', true);
            setTimeout(() => location.reload(), 1200);
        } else {
            showLiveTVMsg(data.detail || JSON.stringify(data), false);
        }
    } catch (e) {
        showLiveTVMsg('Network error: ' + e.message, false);
    }
}

function showLiveTVMsg(msg, ok) {
    const el = document.getElementById('livetv-msg');
    if (!el) return;
    el.textContent   = msg;
    el.style.background = ok ? '#1b5e20' : '#7f0000';
    el.style.color      = ok ? '#a5d6a7' : '#ef9a9a';
    el.style.display    = 'block';
}

// ── Initialisation ────────────────────────────────────────────────────────────
// Filter the library picker based on current channel type
filterLibraryPicker();

// In edit mode: pre-load genres for all libraries already attached to the channel
(async () => {
    const existingLibs = document.querySelectorAll('#lib-list li');
    const fetches = [...existingLibs].map(li => fetchLibraryGenres(li.dataset.id));
    await Promise.all(fetches);
})();
</script>
</body>
</html>
