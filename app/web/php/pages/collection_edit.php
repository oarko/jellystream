<?php
require_once '../config/config.php';
require_once '../includes/api_client.php';

$api        = new ApiClient();
$is_edit    = isset($_GET['id']) && intval($_GET['id']) > 0;
$col_id     = $is_edit ? intval($_GET['id']) : null;
$collection = null;

if ($is_edit) {
    $resp = $api->getCollection($col_id);
    if (!$resp['success']) {
        header('Location: collections.php');
        exit;
    }
    $collection = $resp['data'];
}

// Fetch libraries for the library picker
$lib_resp  = $api->getJellyfinLibraries();
$libraries = $lib_resp['success'] ? ($lib_resp['data']['libraries'] ?? []) : [];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo $is_edit ? 'Edit Collection' : 'New Collection'; ?> - <?php echo APP_NAME; ?></title>
    <link rel="stylesheet" href="/static/css/style.css">
    <style>
        /* ── Two-column layout ─────────────────────────────────────── */
        .col-layout { display:grid; grid-template-columns:1fr 340px; gap:16px; align-items:start; }
        @media(max-width:900px) { .col-layout { grid-template-columns:1fr; } }

        /* ── Browse panel ──────────────────────────────────────────── */
        .browse-controls { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:12px; }
        .browse-controls select,
        .browse-controls input { flex:1; min-width:120px; }
        .type-tabs { display:flex; gap:0; border-radius:6px; overflow:hidden; border:1px solid #333; }
        .type-tab  { padding:7px 16px; cursor:pointer; background:#1a1a1a; color:#aaa; font-size:13px; border:none; }
        .type-tab.active { background:#00A4DC; color:#fff; }
        .breadcrumb { font-size:13px; color:#888; margin-bottom:10px; display:flex; align-items:center; gap:6px; flex-wrap:wrap; min-height:22px; }
        .breadcrumb span { cursor:pointer; color:#00A4DC; }
        .breadcrumb span:last-child { color:#fff; cursor:default; }

        /* ── Media grid ────────────────────────────────────────────── */
        .media-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(140px,1fr)); gap:12px; min-height:200px; }
        .media-card { background:#1a1a1a; border-radius:8px; overflow:hidden; cursor:pointer; position:relative; border:2px solid transparent; transition:border-color .15s; }
        .media-card.selected { border-color:#00A4DC; }
        .media-card img { width:100%; aspect-ratio:2/3; object-fit:cover; display:block; background:#111; }
        .media-card .card-info { padding:8px 6px 6px; }
        .media-card .card-title { font-size:12px; color:#ddd; line-height:1.3; margin-bottom:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .media-card .card-meta { font-size:11px; color:#666; }
        .media-card .card-check { position:absolute; top:6px; right:6px; width:22px; height:22px; border-radius:50%; background:rgba(0,0,0,.6); border:2px solid #555; display:flex; align-items:center; justify-content:center; font-size:13px; }
        .media-card.selected .card-check { background:#00A4DC; border-color:#00A4DC; color:#fff; }
        .media-card .drill-btn { position:absolute; bottom:40px; right:6px; font-size:10px; background:rgba(0,0,0,.7); color:#00A4DC; border:1px solid #00A4DC; border-radius:4px; padding:2px 6px; cursor:pointer; }

        /* ── Episode list (drill-down) ─────────────────────────────── */
        .episode-list { display:flex; flex-direction:column; gap:8px; }
        .episode-row  { display:flex; gap:12px; align-items:flex-start; background:#1a1a1a; border-radius:8px; padding:10px; border:2px solid transparent; }
        .episode-row.selected { border-color:#00A4DC; }
        .episode-thumb { width:80px; height:45px; object-fit:cover; border-radius:4px; flex-shrink:0; background:#111; }
        .ep-info { flex:1; min-width:0; }
        .ep-num   { font-size:11px; color:#888; }
        .ep-title { font-size:13px; color:#ddd; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .ep-meta  { font-size:11px; color:#666; margin-top:2px; }
        .ep-plot  { font-size:12px; color:#888; margin-top:4px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
        .ep-add   { flex-shrink:0; align-self:center; }
        .add-season-row { display:flex; justify-content:flex-end; margin-bottom:8px; }

        /* ── Pagination ────────────────────────────────────────────── */
        .pagination { display:flex; justify-content:space-between; align-items:center; margin-top:14px; font-size:13px; color:#888; }
        .pagination button:disabled { opacity:.4; }

        /* ── Cart panel ────────────────────────────────────────────── */
        .cart-panel { background:#1f1f1f; border-radius:10px; padding:16px; position:sticky; top:16px; }
        .cart-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }
        .cart-header h2 { margin:0; font-size:16px; }
        .cart-clear { font-size:12px; color:#888; cursor:pointer; text-decoration:underline; }
        .cart-items { display:flex; flex-direction:column; gap:6px; max-height:420px; overflow-y:auto; margin-bottom:12px; }
        .cart-item  { display:flex; align-items:center; gap:8px; background:#282828; border-radius:6px; padding:6px 8px; }
        .cart-thumb { width:28px; height:40px; object-fit:cover; border-radius:3px; flex-shrink:0; background:#111; }
        .cart-item-info { flex:1; min-width:0; }
        .cart-item-title { font-size:12px; color:#ddd; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .cart-item-type  { font-size:11px; color:#888; }
        .cart-remove { background:none; border:none; color:#555; cursor:pointer; font-size:16px; line-height:1; flex-shrink:0; padding:0 2px; }
        .cart-remove:hover { color:#e57373; }
        .cart-empty { color:#555; font-size:13px; text-align:center; padding:20px 0; }
        .save-form { border-top:1px solid #2a2a2a; padding-top:12px; }
        .save-form label { display:block; font-size:12px; color:#aaa; margin-bottom:4px; }
        .save-form input, .save-form textarea { width:100%; box-sizing:border-box; margin-bottom:10px; }
        .save-form textarea { height:60px; resize:vertical; }

        #status-msg { margin-bottom:12px; padding:10px 14px; border-radius:6px; display:none; font-size:14px; }
        .loading-msg { color:#888; font-size:13px; text-align:center; padding:24px; }
        .type-badge { font-size:10px; font-weight:700; padding:1px 5px; border-radius:8px; }
        .type-movie   { background:#1b3a6b; color:#90caf9; }
        .type-series  { background:#4a1b6b; color:#ce93d8; }
        .type-season  { background:#6b4a1b; color:#ffcc80; }
        .type-episode { background:#1b6b2a; color:#a5d6a7; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1><?php echo $is_edit ? '✏️ Edit Collection' : '📦 New Collection'; ?></h1>
        <a href="collections.php" class="btn btn-secondary">← Collections</a>
    </div>

    <div id="status-msg"></div>

    <div class="col-layout">
        <!-- ════════ LEFT: Browse Panel ════════ -->
        <div>
            <div class="card" style="margin-bottom:0;">
                <h2 style="margin-top:0;">Browse Media</h2>

                <!-- Controls row -->
                <div class="browse-controls">
                    <select id="lib-select" onchange="onLibraryChange()">
                        <option value="">— Select library —</option>
                        <?php foreach ($libraries as $lib): ?>
                            <?php
                            $type = $lib['CollectionType'] ?? '';
                            if (!in_array($type, ['movies','tvshows','mixed','boxsets'])) continue;
                            ?>
                            <option value="<?php echo htmlspecialchars($lib['ItemId']); ?>"
                                    data-type="<?php echo htmlspecialchars($type); ?>">
                                <?php echo htmlspecialchars($lib['Name']); ?>
                            </option>
                        <?php endforeach; ?>
                    </select>

                    <div class="type-tabs">
                        <button class="type-tab active" id="tab-movie"  onclick="setType('Movie')">Movies</button>
                        <button class="type-tab"        id="tab-series" onclick="setType('Series')">Series</button>
                    </div>
                </div>

                <div class="browse-controls">
                    <input type="text" id="search-input" placeholder="Search…" onkeydown="if(event.key==='Enter')doSearch()">
                    <input type="number" id="year-from" placeholder="Year from" min="1900" max="2099" style="width:100px;flex:none;">
                    <input type="number" id="year-to"   placeholder="Year to"   min="1900" max="2099" style="width:100px;flex:none;">
                    <button class="btn btn-secondary" onclick="doSearch()">Search</button>
                    <button class="btn btn-secondary" onclick="clearSearch()" title="Clear search">✕</button>
                </div>

                <!-- Breadcrumb -->
                <div class="breadcrumb" id="breadcrumb"></div>

                <!-- Media area -->
                <div id="media-area">
                    <div class="loading-msg">Select a library to start browsing.</div>
                </div>

                <!-- Pagination -->
                <div class="pagination" id="pagination" style="display:none;">
                    <button class="btn btn-secondary btn-sm" id="btn-prev" onclick="changePage(-1)">← Prev</button>
                    <span id="page-info"></span>
                    <button class="btn btn-secondary btn-sm" id="btn-next" onclick="changePage(1)">Next →</button>
                </div>
            </div>
        </div>

        <!-- ════════ RIGHT: Cart Panel ════════ -->
        <div>
            <div class="cart-panel">
                <div class="cart-header">
                    <h2>Selected Items (<span id="cart-count">0</span>)</h2>
                    <span class="cart-clear" onclick="clearCart()">Clear All</span>
                </div>
                <div class="cart-items" id="cart-items">
                    <div class="cart-empty" id="cart-empty">No items selected yet.</div>
                </div>

                <div class="save-form">
                    <label for="col-name">Collection Name *</label>
                    <input type="text" id="col-name"
                           value="<?php echo htmlspecialchars($collection['name'] ?? ''); ?>"
                           placeholder="My Collection">
                    <label for="col-desc">Description</label>
                    <textarea id="col-desc" placeholder="Optional description…"><?php echo htmlspecialchars($collection['description'] ?? ''); ?></textarea>
                    <button class="btn btn-primary" style="width:100%;" onclick="saveCollection()">
                        <?php echo $is_edit ? 'Update Collection' : 'Save Collection'; ?>
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
const API_BASE   = '<?php echo getApiBaseUrl(); ?>';
const IS_EDIT    = <?php echo $is_edit ? 'true' : 'false'; ?>;
const COLLECTION_ID = <?php echo $col_id ?? 'null'; ?>;

// ─── State ────────────────────────────────────────────────────────────────
const cart = new Map();   // media_item_id → item data

let browseState = {
    libraryId: '',
    type: 'Movie',
    search: '',
    yearFrom: null,
    yearTo: null,
    page: 0,
    limit: 24,
    totalItems: 0,
    // drill-down
    mode: 'browse',       // 'browse' | 'seasons' | 'episodes'
    seriesId: null, seriesTitle: '',
    seasonId: null, seasonTitle: '',
    seasonNumber: null,
    seriesLibraryId: '',
};

// ─── Initialise existing collection items ────────────────────────────────
<?php if ($is_edit && $collection): ?>
(function(){
    const existing = <?php echo json_encode($collection['items'] ?? []); ?>;
    for (const item of existing) {
        cart.set(item.media_item_id, {
            media_item_id:  item.media_item_id,
            item_type:      item.item_type,
            title:          item.title,
            library_id:     item.library_id,
            series_name:    item.series_name || null,
            season_number:  item.season_number || null,
            episode_number: item.episode_number || null,
            duration:       item.duration || null,
            genres:         item.genres || null,
            file_path:      item.file_path || null,
        });
    }
    renderCart();
})();
<?php endif; ?>

// ─── Library / type controls ──────────────────────────────────────────────
function onLibraryChange() {
    const sel = document.getElementById('lib-select');
    browseState.libraryId = sel.value;
    browseState.page = 0;
    resetDrill();
    if (browseState.libraryId) browse();
    else showPlaceholder('Select a library to start browsing.');
}

function setType(type) {
    browseState.type = type;
    browseState.page = 0;
    document.getElementById('tab-movie').classList.toggle('active', type === 'Movie');
    document.getElementById('tab-series').classList.toggle('active', type === 'Series');
    resetDrill();
    if (browseState.libraryId) browse();
}

function doSearch() {
    browseState.search   = document.getElementById('search-input').value.trim();
    browseState.yearFrom = parseInt(document.getElementById('year-from').value) || null;
    browseState.yearTo   = parseInt(document.getElementById('year-to').value)   || null;
    browseState.page = 0;
    resetDrill();
    if (browseState.libraryId) browse();
}

function clearSearch() {
    document.getElementById('search-input').value = '';
    document.getElementById('year-from').value    = '';
    document.getElementById('year-to').value      = '';
    browseState.search = '';
    browseState.yearFrom = null;
    browseState.yearTo   = null;
    browseState.page = 0;
    if (browseState.libraryId) browse();
}

function changePage(delta) {
    browseState.page = Math.max(0, browseState.page + delta);
    browse();
}

function resetDrill() {
    browseState.mode = 'browse';
    browseState.seriesId = null;
    browseState.seasonId = null;
    renderBreadcrumb();
}

// ─── Browse (grid) ────────────────────────────────────────────────────────
async function browse() {
    const { libraryId, type, search, yearFrom, yearTo, page, limit } = browseState;
    showLoading();

    const params = new URLSearchParams({
        library_id: libraryId,
        type:       type,
        limit:      limit,
        offset:     page * limit,
    });
    if (search)   params.set('search',    search);
    if (yearFrom) params.set('year_from', yearFrom);
    if (yearTo)   params.set('year_to',   yearTo);

    try {
        const resp = await fetch(`${API_BASE}/jellyfin/browse?${params}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        browseState.totalItems = data.TotalRecordCount || 0;
        renderGrid(data.Items || [], type);
        renderPagination();
        renderBreadcrumb();
    } catch (e) {
        showPlaceholder(`Error: ${e.message}`);
        hidePagination();
    }
}

function renderGrid(items, type) {
    const area = document.getElementById('media-area');
    if (items.length === 0) {
        area.innerHTML = '<div class="loading-msg">No items found.</div>';
        return;
    }
    const isSeries = type === 'Series';
    area.innerHTML = '';
    const grid = document.createElement('div');
    grid.className = 'media-grid';

    for (const item of items) {
        const id       = item.Id || '';
        const title    = item.Name || '';
        const year     = item.ProductionYear || '';
        const imgUrl   = `${API_BASE}/jellyfin/items/${encodeURIComponent(id)}/image?type=Primary&maxWidth=280`;
        const inCart   = cart.has(id);
        const libId    = item.ParentId || browseState.libraryId;
        const ticks    = item.RunTimeTicks || 0;
        const duration = ticks ? Math.round(ticks / 10000000) : null;

        const card = document.createElement('div');
        card.className = `media-card${inCart ? ' selected' : ''}`;
        card.dataset.id = id;
        card.innerHTML = `
            <img src="${esc(imgUrl)}" alt="${esc(title)}" loading="lazy"
                 onerror="this.style.display='none'">
            <div class="card-check">${inCart ? '✓' : ''}</div>
            ${isSeries ? `<button class="drill-btn" onclick="drillSeries('${esc(id)}','${esc(title)}','${esc(libId)}',event)">▶ Seasons</button>` : ''}
            <div class="card-info">
                <div class="card-title" title="${esc(title)}">${esc(title)}</div>
                <div class="card-meta">${year}</div>
            </div>
        `;
        card.addEventListener('click', () => toggleCartFromCard(card, {
            media_item_id:  id,
            item_type:      isSeries ? 'Series' : 'Movie',
            title:          title,
            library_id:     libId,
            duration:       duration,
            genres:         item.Genres ? JSON.stringify(item.Genres) : null,
            file_path:      extractPath(item),
        }));
        grid.appendChild(card);
    }
    area.appendChild(grid);
}

// ─── Season drill-down ────────────────────────────────────────────────────
async function drillSeries(seriesId, seriesTitle, libId, event) {
    event.stopPropagation();   // don't toggle cart
    browseState.mode        = 'seasons';
    browseState.seriesId    = seriesId;
    browseState.seriesTitle = seriesTitle;
    browseState.seriesLibraryId = libId;
    showLoading();
    hidePagination();
    renderBreadcrumb();

    try {
        const resp = await fetch(`${API_BASE}/jellyfin/series/${encodeURIComponent(seriesId)}/seasons`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        renderSeasonGrid(data.Items || [], seriesId, seriesTitle, libId);
    } catch (e) {
        showPlaceholder(`Error loading seasons: ${e.message}`);
    }
}

function renderSeasonGrid(seasons, seriesId, seriesTitle, libId) {
    const area = document.getElementById('media-area');
    if (seasons.length === 0) {
        area.innerHTML = '<div class="loading-msg">No seasons found.</div>';
        return;
    }
    area.innerHTML = '';
    const grid = document.createElement('div');
    grid.className = 'media-grid';

    for (const s of seasons) {
        const id      = s.Id || '';
        const sNum    = s.IndexNumber || null;
        const title   = s.Name || `Season ${sNum}`;
        const imgUrl  = `${API_BASE}/jellyfin/items/${encodeURIComponent(id)}/image?type=Primary&maxWidth=280`;
        const inCart  = cart.has(id);

        const card = document.createElement('div');
        card.className = `media-card${inCart ? ' selected' : ''}`;
        card.dataset.id = id;
        card.innerHTML = `
            <img src="${esc(imgUrl)}" alt="${esc(title)}" loading="lazy"
                 onerror="this.style.display='none'">
            <div class="card-check">${inCart ? '✓' : ''}</div>
            <button class="drill-btn" onclick="drillSeason('${esc(id)}','${esc(title)}',${sNum || 0},event)">▶ Episodes</button>
            <div class="card-info">
                <div class="card-title" title="${esc(title)}">${esc(title)}</div>
                <div class="card-meta">${seriesTitle}</div>
            </div>
        `;
        card.addEventListener('click', () => toggleCartFromCard(card, {
            media_item_id: id,
            item_type:     'Season',
            title:         title,
            series_name:   seriesTitle,
            season_number: sNum,
            library_id:    libId,
            file_path:     extractPath(s),
        }));
        grid.appendChild(card);
    }
    area.appendChild(grid);
}

// ─── Episode drill-down ───────────────────────────────────────────────────
async function drillSeason(seasonId, seasonTitle, seasonNumber, event) {
    event.stopPropagation();
    browseState.mode         = 'episodes';
    browseState.seasonId     = seasonId;
    browseState.seasonTitle  = seasonTitle;
    browseState.seasonNumber = seasonNumber;
    showLoading();
    hidePagination();
    renderBreadcrumb();

    try {
        const resp = await fetch(`${API_BASE}/jellyfin/seasons/${encodeURIComponent(seasonId)}/episodes`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        renderEpisodeList(data.Items || [], seasonId, seasonTitle, seasonNumber);
    } catch (e) {
        showPlaceholder(`Error loading episodes: ${e.message}`);
    }
}

function renderEpisodeList(episodes, seasonId, seasonTitle, seasonNumber) {
    const area = document.getElementById('media-area');
    if (episodes.length === 0) {
        area.innerHTML = '<div class="loading-msg">No episodes found.</div>';
        return;
    }
    area.innerHTML = '';

    // "Add whole season" button
    const addRow = document.createElement('div');
    addRow.className = 'add-season-row';
    const inCartSeason = cart.has(seasonId);
    addRow.innerHTML = `
        <button class="btn btn-sm ${inCartSeason ? 'btn-secondary' : 'btn-primary'}"
                id="add-season-btn"
                onclick="toggleSeasonInCart('${esc(seasonId)}','${esc(seasonTitle)}',${seasonNumber})">
            ${inCartSeason ? '✓ Season in cart' : '+ Add whole season'}
        </button>
    `;
    area.appendChild(addRow);

    const list = document.createElement('div');
    list.className = 'episode-list';

    for (const ep of episodes) {
        const id      = ep.Id || '';
        const epNum   = ep.IndexNumber || null;
        const sNum    = ep.ParentIndexNumber || seasonNumber;
        const title   = ep.Name || `Episode ${epNum}`;
        const thumbUrl = `${API_BASE}/jellyfin/items/${encodeURIComponent(id)}/image?type=Thumb&maxWidth=160`;
        const ticks   = ep.RunTimeTicks || 0;
        const dur     = ticks ? Math.round(ticks / 10000000) : null;
        const durStr  = dur ? `${Math.floor(dur/60)}m` : '';
        const overview = ep.Overview || '';
        const inCart  = cart.has(id);

        const row = document.createElement('div');
        row.className  = `episode-row${inCart ? ' selected' : ''}`;
        row.dataset.id = id;
        row.innerHTML = `
            <img class="episode-thumb" src="${esc(thumbUrl)}" alt=""
                 onerror="this.src=''" loading="lazy">
            <div class="ep-info">
                <div class="ep-num">S${String(sNum).padStart(2,'0')}E${String(epNum||0).padStart(2,'0')}</div>
                <div class="ep-title">${esc(title)}</div>
                <div class="ep-meta">${durStr}</div>
                ${overview ? `<div class="ep-plot">${esc(overview)}</div>` : ''}
            </div>
            <div class="ep-add">
                <button class="btn btn-sm ${inCart ? 'btn-secondary' : 'btn-primary'}" id="ep-btn-${esc(id)}"
                        onclick="toggleEpisodeInCart('${esc(id)}','${esc(title)}',${sNum},${epNum||0},'${esc(dur)}')">
                    ${inCart ? '✓' : '+'}
                </button>
            </div>
        `;
        list.appendChild(row);
    }
    area.appendChild(list);
}

// ─── Cart helpers ─────────────────────────────────────────────────────────
function toggleCartFromCard(card, itemData) {
    const id = itemData.media_item_id;
    if (cart.has(id)) {
        cart.delete(id);
        card.classList.remove('selected');
        card.querySelector('.card-check').textContent = '';
    } else {
        cart.set(id, itemData);
        card.classList.add('selected');
        card.querySelector('.card-check').textContent = '✓';
    }
    renderCart();
}

function toggleSeasonInCart(seasonId, seasonTitle, seasonNumber) {
    const libId = browseState.seriesLibraryId || browseState.libraryId;
    if (cart.has(seasonId)) {
        cart.delete(seasonId);
    } else {
        cart.set(seasonId, {
            media_item_id: seasonId,
            item_type:     'Season',
            title:         seasonTitle,
            series_name:   browseState.seriesTitle,
            season_number: seasonNumber,
            library_id:    libId,
        });
    }
    // Re-render the season row header
    const btn = document.getElementById('add-season-btn');
    if (btn) {
        const inCart = cart.has(seasonId);
        btn.textContent = inCart ? '✓ Season in cart' : '+ Add whole season';
        btn.className   = `btn btn-sm ${inCart ? 'btn-secondary' : 'btn-primary'}`;
    }
    renderCart();
}

function toggleEpisodeInCart(epId, title, seasonNum, epNum, duration) {
    const libId = browseState.seriesLibraryId || browseState.libraryId;
    const row   = document.querySelector(`[data-id="${epId}"]`);
    const btn   = document.getElementById(`ep-btn-${epId}`);
    if (cart.has(epId)) {
        cart.delete(epId);
        if (row) row.classList.remove('selected');
        if (btn) { btn.textContent = '+'; btn.className = 'btn btn-sm btn-primary'; }
    } else {
        cart.set(epId, {
            media_item_id:  epId,
            item_type:      'Episode',
            title:          title,
            series_name:    browseState.seriesTitle,
            season_number:  seasonNum,
            episode_number: epNum,
            library_id:     libId,
            duration:       duration ? parseInt(duration) : null,
        });
        if (row) row.classList.add('selected');
        if (btn) { btn.textContent = '✓'; btn.className = 'btn btn-sm btn-secondary'; }
    }
    renderCart();
}

function addToCart(item) {
    cart.set(item.media_item_id, item);
    renderCart();
}

function removeFromCart(id) {
    cart.delete(id);
    renderCart();
    // Deselect any visible card/row
    const el = document.querySelector(`[data-id="${id}"]`);
    if (el) {
        el.classList.remove('selected');
        const check = el.querySelector('.card-check');
        if (check) check.textContent = '';
        const btn = el.querySelector('.ep-add button');
        if (btn) { btn.textContent = '+'; btn.className = 'btn btn-sm btn-primary'; }
    }
    const epBtn = document.getElementById(`ep-btn-${id}`);
    if (epBtn) { epBtn.textContent = '+'; epBtn.className = 'btn btn-sm btn-primary'; }
}

function clearCart() {
    cart.clear();
    renderCart();
    document.querySelectorAll('.media-card.selected, .episode-row.selected').forEach(el => {
        el.classList.remove('selected');
        const check = el.querySelector('.card-check');
        if (check) check.textContent = '';
    });
}

function renderCart() {
    const container = document.getElementById('cart-items');
    const empty     = document.getElementById('cart-empty');
    document.getElementById('cart-count').textContent = cart.size;

    if (cart.size === 0) {
        container.innerHTML = '';
        empty.style.display = 'block';
        return;
    }
    empty.style.display = 'none';
    container.innerHTML = '';

    for (const [id, item] of cart) {
        const thumbUrl = `${API_BASE}/jellyfin/items/${encodeURIComponent(id)}/image?type=Primary&maxWidth=60`;
        const typeLabel = item.item_type || 'Item';
        const typeCls   = {Movie:'type-movie', Series:'type-series', Season:'type-season', Episode:'type-episode'}[typeLabel] || '';
        const subtitle  = item.series_name
            ? (item.season_number ? `S${String(item.season_number).padStart(2,'0')}` : '') + ' ' + item.series_name
            : '';

        const div = document.createElement('div');
        div.className = 'cart-item';
        div.innerHTML = `
            <img class="cart-thumb" src="${esc(thumbUrl)}" alt=""
                 onerror="this.style.display='none'" loading="lazy">
            <div class="cart-item-info">
                <div class="cart-item-title" title="${esc(item.title)}">${esc(item.title)}</div>
                <div class="cart-item-type">
                    <span class="type-badge ${typeCls}">${esc(typeLabel)}</span>
                    ${subtitle ? `<span style="color:#666;font-size:11px;"> ${esc(subtitle.trim())}</span>` : ''}
                </div>
            </div>
            <button class="cart-remove" onclick="removeFromCart('${esc(id)}')" title="Remove">✕</button>
        `;
        container.appendChild(div);
    }
}

// ─── Save ─────────────────────────────────────────────────────────────────
async function saveCollection() {
    const name = document.getElementById('col-name').value.trim();
    if (!name) { showStatus('Collection name is required.', false); return; }
    if (cart.size === 0) { showStatus('Add at least one item to the collection.', false); return; }

    const items = [...cart.values()].map((item, idx) => ({
        media_item_id:  item.media_item_id,
        item_type:      item.item_type,
        title:          item.title,
        library_id:     item.library_id || '',
        series_name:    item.series_name || null,
        season_number:  item.season_number || null,
        episode_number: item.episode_number || null,
        duration:       item.duration || null,
        genres:         item.genres || null,
        file_path:      item.file_path || null,
        sort_order:     idx,
    }));

    const payload = {
        name:        name,
        description: document.getElementById('col-desc').value.trim() || null,
        items:       items,
    };

    const url    = IS_EDIT ? `${API_BASE}/collections/${COLLECTION_ID}` : `${API_BASE}/collections/`;
    const method = IS_EDIT ? 'PUT' : 'POST';

    try {
        const resp = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await resp.json();
        if (resp.ok) {
            showStatus(data.message || 'Saved!', true);
            setTimeout(() => { window.location.href = 'collections.php'; }, 1200);
        } else {
            showStatus(data.detail || JSON.stringify(data), false);
        }
    } catch (e) {
        showStatus('Network error: ' + e.message, false);
    }
}

// ─── Breadcrumb ───────────────────────────────────────────────────────────
function renderBreadcrumb() {
    const bc = document.getElementById('breadcrumb');
    const parts = [];
    if (browseState.libraryId) {
        const sel = document.getElementById('lib-select');
        const libName = sel.options[sel.selectedIndex]?.text || 'Library';
        parts.push({ label: libName, action: () => { resetDrill(); browse(); }});
    }
    if (browseState.mode === 'seasons' || browseState.mode === 'episodes') {
        parts.push({ label: browseState.seriesTitle, action: () => {
            browseState.mode = 'seasons';
            browseState.seasonId = null;
            renderBreadcrumb();
            drillSeriesDirect();
        }});
    }
    if (browseState.mode === 'episodes') {
        parts.push({ label: browseState.seasonTitle, action: null });
    }

    bc.innerHTML = parts.map((p, i) => {
        if (i < parts.length - 1 && p.action) {
            return `<span onclick="(${p.action.toString()})()">${esc(p.label)}</span> /`;
        }
        return `<span>${esc(p.label)}</span>`;
    }).join(' ');
}

async function drillSeriesDirect() {
    showLoading();
    hidePagination();
    try {
        const resp = await fetch(`${API_BASE}/jellyfin/series/${encodeURIComponent(browseState.seriesId)}/seasons`);
        const data = await resp.json();
        renderSeasonGrid(data.Items || [], browseState.seriesId, browseState.seriesTitle, browseState.seriesLibraryId);
    } catch (e) {
        showPlaceholder(`Error: ${e.message}`);
    }
}

// ─── Pagination ───────────────────────────────────────────────────────────
function renderPagination() {
    const { page, limit, totalItems } = browseState;
    const totalPages = Math.ceil(totalItems / limit) || 1;
    document.getElementById('pagination').style.display = 'flex';
    document.getElementById('page-info').textContent =
        `Page ${page + 1} of ${totalPages}  (${totalItems} items)`;
    document.getElementById('btn-prev').disabled = page === 0;
    document.getElementById('btn-next').disabled = (page + 1) * limit >= totalItems;
}

function hidePagination() {
    document.getElementById('pagination').style.display = 'none';
}

// ─── UI helpers ───────────────────────────────────────────────────────────
function showLoading() {
    document.getElementById('media-area').innerHTML =
        '<div class="loading-msg">Loading…</div>';
}

function showPlaceholder(msg) {
    document.getElementById('media-area').innerHTML =
        `<div class="loading-msg">${esc(msg)}</div>`;
}

function showStatus(msg, ok) {
    const el = document.getElementById('status-msg');
    el.textContent = msg;
    el.className   = ok ? 'status-ok' : 'status-err';
    el.style.display = 'block';
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function extractPath(item) {
    const p = item.Path;
    if (p) return p;
    const src = (item.MediaSources || [])[0];
    return src ? (src.Path || null) : null;
}

function esc(s) {
    return String(s ?? '')
        .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
        .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
</script>
</body>
</html>
