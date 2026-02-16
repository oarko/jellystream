<?php
require_once '../config/config.php';
require_once '../includes/api_client.php';
require_once '../includes/database.php';

$api = new ApiClient();
$db = new Database();

$stream_id = isset($_GET['id']) ? intval($_GET['id']) : null;
$is_edit = $stream_id !== null;

// Get stream data if editing
$stream = null;
$schedules = [];
if ($is_edit) {
    $stream_response = $api->getStream($stream_id);
    if ($stream_response['success']) {
        $stream = $stream_response['data'];
    } else {
        die('Stream not found');
    }

    // Get schedules for this stream
    $schedules_response = $api->getStreamSchedules($stream_id);
    if ($schedules_response['success']) {
        $schedules = $schedules_response['data'];
    }
}

// Get Jellyfin libraries
$libraries_response = $api->getJellyfinLibraries();
$libraries = $libraries_response['success'] && isset($libraries_response['data']['libraries'])
    ? $libraries_response['data']['libraries']
    : [];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo $is_edit ? 'Edit' : 'Create'; ?> Stream - <?php echo APP_NAME; ?></title>
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
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: #1F1F1F;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .layout {
            display: grid;
            grid-template-columns: 350px 1fr;
            gap: 20px;
        }
        .sidebar {
            background: #1F1F1F;
            padding: 20px;
            border-radius: 8px;
            height: fit-content;
            position: sticky;
            top: 20px;
        }
        .main-content {
            background: #1F1F1F;
            padding: 20px;
            border-radius: 8px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #aaa;
        }
        input, select, textarea {
            width: 100%;
            padding: 10px;
            background: #282828;
            border: 1px solid #444;
            border-radius: 5px;
            color: #fff;
            box-sizing: border-box;
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
        .btn-sm {
            padding: 5px 10px;
            font-size: 12px;
        }

        /* Breadcrumb Navigation */
        .breadcrumb {
            background: #282828;
            padding: 10px 15px;
            border-radius: 5px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .breadcrumb-item {
            color: #00A4DC;
            cursor: pointer;
            text-decoration: underline;
        }
        .breadcrumb-item:hover {
            opacity: 0.8;
        }
        .breadcrumb-separator {
            color: #666;
        }
        .breadcrumb-current {
            color: #fff;
            cursor: default;
            text-decoration: none;
        }

        /* Jellyfin Browser */
        .jellyfin-browser {
            margin-top: 20px;
        }
        .library-selector {
            margin-bottom: 15px;
        }
        .search-box {
            margin-bottom: 15px;
        }
        .media-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 15px;
            padding: 10px;
            background: #282828;
            border-radius: 5px;
        }
        .media-item {
            background: #333;
            border-radius: 5px;
            padding: 10px;
            cursor: pointer;
            transition: transform 0.2s, background 0.2s;
            text-align: center;
            position: relative;
        }
        .media-item:hover {
            background: #444;
            transform: scale(1.05);
        }
        .media-item.browsable {
            border: 2px solid #00A4DC;
        }
        .media-item.selected {
            border: 2px solid #28a745;
        }
        .media-poster {
            width: 100%;
            height: 200px;
            object-fit: cover;
            border-radius: 3px;
            background: #222;
            margin-bottom: 8px;
        }
        .media-title {
            font-size: 13px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .media-type {
            font-size: 11px;
            color: #888;
            margin-top: 3px;
        }
        .media-duration {
            font-size: 11px;
            color: #00A4DC;
            margin-top: 3px;
        }
        .browse-badge {
            position: absolute;
            top: 5px;
            right: 5px;
            background: #00A4DC;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: bold;
        }

        /* Pagination */
        .pagination {
            text-align: center;
            padding: 15px;
            background: #282828;
            border-radius: 5px;
            margin-top: 15px;
        }
        .pagination-info {
            color: #888;
            margin-bottom: 10px;
        }

        /* Schedule Builder */
        .schedule-builder {
            margin-top: 20px;
        }
        .schedule-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .schedule-list {
            background: #282828;
            border-radius: 5px;
            padding: 15px;
            max-height: 500px;
            overflow-y: auto;
        }
        .schedule-item {
            background: #333;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
            border-left: 4px solid #00A4DC;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .schedule-item.movie {
            border-left-color: #28a745;
        }
        .schedule-item.episode {
            border-left-color: #ffc107;
        }
        .schedule-info {
            flex: 1;
        }
        .schedule-time {
            font-size: 14px;
            color: #00A4DC;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .schedule-title {
            font-size: 16px;
            margin-bottom: 3px;
        }
        .schedule-meta {
            font-size: 12px;
            color: #888;
        }
        .schedule-actions {
            display: flex;
            gap: 5px;
        }
        .empty-schedule {
            text-align: center;
            padding: 40px;
            color: #888;
        }
        .selected-media-info {
            background: #282828;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 15px;
            display: none;
        }
        .selected-media-info.show {
            display: block;
        }
        .add-to-schedule-form {
            background: #333;
            padding: 15px;
            border-radius: 5px;
            margin-top: 10px;
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: #888;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><?php echo $is_edit ? 'Edit Stream' : 'Create New Stream'; ?></h1>
            <a href="/index.php" class="btn btn-secondary">← Back to Dashboard</a>
        </div>

        <div class="layout">
            <!-- Sidebar: Stream Info -->
            <div class="sidebar">
                <h2>Stream Details</h2>
                <form id="streamForm">
                    <input type="hidden" name="stream_id" value="<?php echo $stream_id ?? ''; ?>">

                    <div class="form-group">
                        <label for="stream_name">Stream Name *</label>
                        <input type="text" id="stream_name" name="name"
                               value="<?php echo htmlspecialchars($stream['name'] ?? ''); ?>"
                               required>
                    </div>

                    <div class="form-group">
                        <label for="stream_description">Description</label>
                        <textarea id="stream_description" name="description" rows="3"><?php echo htmlspecialchars($stream['description'] ?? ''); ?></textarea>
                    </div>

                    <div class="form-group">
                        <label for="jellyfin_library">Jellyfin Library *</label>
                        <select id="jellyfin_library" name="jellyfin_library_id" required>
                            <option value="">-- Select Library --</option>
                            <?php foreach ($libraries as $library): ?>
                                <option value="<?php echo htmlspecialchars($library['Id']); ?>"
                                        data-type="<?php echo htmlspecialchars($library['CollectionType'] ?? 'mixed'); ?>"
                                        <?php echo ($stream['jellyfin_library_id'] ?? '') === $library['Id'] ? 'selected' : ''; ?>>
                                    <?php echo htmlspecialchars($library['Name']); ?>
                                </option>
                            <?php endforeach; ?>
                        </select>
                    </div>

                    <button type="submit" class="btn"><?php echo $is_edit ? 'Update' : 'Create'; ?> Stream</button>
                </form>
            </div>

            <!-- Main Content: Schedule Builder -->
            <div class="main-content">
                <div class="schedule-builder">
                    <div class="schedule-header">
                        <h2>Schedule / Timeline</h2>
                        <div class="schedule-controls">
                            <span id="scheduleCount">0 items scheduled</span>
                        </div>
                    </div>

                    <div class="schedule-list" id="scheduleList">
                        <div class="empty-schedule">
                            <p>📺 No items scheduled yet</p>
                            <p style="font-size: 14px; color: #666;">Browse Jellyfin content below to add items to your schedule</p>
                        </div>
                    </div>
                </div>

                <!-- Jellyfin Content Browser -->
                <div class="jellyfin-browser">
                    <h2>Browse Jellyfin Content</h2>

                    <div class="library-selector">
                        <label for="browse_library">Select Library to Browse</label>
                        <select id="browse_library">
                            <option value="">-- Select Library --</option>
                            <?php foreach ($libraries as $library): ?>
                                <option value="<?php echo htmlspecialchars($library['Id']); ?>"
                                        data-type="<?php echo htmlspecialchars($library['CollectionType'] ?? 'mixed'); ?>"
                                        data-name="<?php echo htmlspecialchars($library['Name']); ?>">
                                    <?php echo htmlspecialchars($library['Name']); ?>
                                    (<?php echo htmlspecialchars($library['CollectionType'] ?? 'mixed'); ?>)
                                </option>
                            <?php endforeach; ?>
                        </select>
                    </div>

                    <!-- Breadcrumb Navigation -->
                    <div class="breadcrumb" id="breadcrumb" style="display: none;"></div>

                    <!-- Sort Controls -->
                    <div class="sort-controls" style="display: grid; grid-template-columns: 2fr 1fr; gap: 10px; margin-bottom: 15px;">
                        <div class="form-group" style="margin-bottom: 0;">
                            <label for="sortBy">Sort By</label>
                            <select id="sortBy" onchange="onSortChange()">
                                <option value="SortName">Name (A-Z)</option>
                                <option value="DateCreated">Date Created</option>
                                <option value="PremiereDate">Premiere Date</option>
                                <option value="DatePlayed">Date Played</option>
                                <option value="ProductionYear">Production Year</option>
                                <option value="CommunityRating">Community Rating</option>
                                <option value="CriticRating">Critic Rating</option>
                                <option value="OfficialRating">Official Rating</option>
                                <option value="Runtime">Runtime</option>
                                <option value="PlayCount">Play Count</option>
                                <option value="IsUnplayed">Unplayed First</option>
                                <option value="IsPlayed">Played First</option>
                                <option value="DateLastContentAdded">Recently Added</option>
                                <option value="SeriesSortName">Series Name</option>
                                <option value="SeriesDatePlayed">Series Date Played</option>
                                <option value="AiredEpisodeOrder">Aired Episode Order</option>
                                <option value="Random">Random</option>
                            </select>
                        </div>
                        <div class="form-group" style="margin-bottom: 0;">
                            <label for="sortOrder">Order</label>
                            <select id="sortOrder" onchange="onSortChange()">
                                <option value="Ascending">Ascending ↑</option>
                                <option value="Descending">Descending ↓</option>
                            </select>
                        </div>
                    </div>

                    <div class="search-box">
                        <input type="text" id="mediaSearch" placeholder="🔍 Search by title...">
                    </div>

                    <div class="selected-media-info" id="selectedMediaInfo">
                        <h3>Selected: <span id="selectedMediaTitle"></span></h3>
                        <div class="add-to-schedule-form">
                            <div class="form-group">
                                <label for="schedule_time">Scheduled Time</label>
                                <input type="datetime-local" id="schedule_time">
                            </div>
                            <button class="btn" onclick="addToSchedule()">Add to Schedule</button>
                            <button class="btn btn-secondary" onclick="clearSelection()">Cancel</button>
                        </div>
                    </div>

                    <div class="media-grid" id="mediaGrid">
                        <div class="loading">Select a library to browse content</div>
                    </div>

                    <!-- Pagination -->
                    <div class="pagination" id="pagination" style="display: none;">
                        <div class="pagination-info" id="paginationInfo"></div>
                        <button class="btn" id="loadMoreBtn" onclick="loadMore()">Load More</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let selectedMedia = null;
        let schedules = <?php echo json_encode($schedules); ?>;
        let allMedia = [];

        // Navigation state
        let currentLibraryId = null;
        let currentLibraryType = null;
        let currentParentId = null;
        let navigationPath = [];

        // Pagination state
        let currentPage = 0;
        let pageSize = 50;
        let totalRecordCount = 0;
        let startIndex = 0;

        // Load library items when library is selected
        document.getElementById('browse_library').addEventListener('change', async function() {
            const libraryId = this.value;
            const selectedOption = this.options[this.selectedIndex];
            const libraryType = selectedOption.dataset.type;
            const libraryName = selectedOption.dataset.name;

            if (!libraryId) {
                document.getElementById('mediaGrid').innerHTML = '<div class="loading">Select a library to browse content</div>';
                document.getElementById('breadcrumb').style.display = 'none';
                document.getElementById('pagination').style.display = 'none';
                return;
            }

            currentLibraryId = libraryId;
            currentLibraryType = libraryType;
            currentParentId = libraryId;
            navigationPath = [{id: libraryId, name: libraryName, type: 'Library'}];

            loadItems(libraryId, true);
        });

        // Load items from a parent (library, series, season)
        async function loadItems(parentId, reset = false) {
            if (reset) {
                startIndex = 0;
                allMedia = [];
            }

            document.getElementById('mediaGrid').innerHTML = '<div class="loading">Loading...</div>';

            try {
                // Get current sort options from dropdowns
                const sortBy = document.getElementById('sortBy').value;
                const sortOrder = document.getElementById('sortOrder').value;

                const url = new URL(`<?php echo API_BASE_URL; ?>/jellyfin/items/${parentId}`);
                url.searchParams.set('recursive', 'false'); // Hierarchical browsing
                url.searchParams.set('limit', pageSize);
                url.searchParams.set('start_index', startIndex);
                url.searchParams.set('sort_by', sortBy);
                url.searchParams.set('sort_order', sortOrder);

                const response = await fetch(url);
                const data = await response.json();

                if (data.Items) {
                    if (reset) {
                        allMedia = data.Items;
                    } else {
                        allMedia = allMedia.concat(data.Items);
                    }
                    totalRecordCount = data.TotalRecordCount || 0;
                    startIndex = data.StartIndex || 0;

                    renderMediaGrid(allMedia);
                    updatePagination();
                    updateBreadcrumb();
                } else {
                    document.getElementById('mediaGrid').innerHTML = '<div class="loading">No items found</div>';
                }
            } catch (error) {
                console.error('Error loading items:', error);
                document.getElementById('mediaGrid').innerHTML = '<div class="loading">Error loading items</div>';
            }
        }

        // Navigate into a browsable item (Series or Season)
        function navigateInto(item) {
            if (item.Type === 'Series' || item.Type === 'Season') {
                currentParentId = item.Id;
                navigationPath.push({id: item.Id, name: item.Name, type: item.Type});
                loadItems(item.Id, true);
            } else if (item.Type === 'Episode' || item.Type === 'Movie') {
                selectMedia(item);
            }
        }

        // Navigate to a specific level in the path
        function navigateTo(index) {
            if (index < 0 || index >= navigationPath.length) return;

            navigationPath = navigationPath.slice(0, index + 1);
            const target = navigationPath[index];
            currentParentId = target.id;
            loadItems(target.id, true);
        }

        // Update breadcrumb navigation
        function updateBreadcrumb() {
            const breadcrumb = document.getElementById('breadcrumb');

            if (navigationPath.length === 0) {
                breadcrumb.style.display = 'none';
                return;
            }

            breadcrumb.style.display = 'flex';
            breadcrumb.innerHTML = navigationPath.map((item, index) => {
                const isLast = index === navigationPath.length - 1;
                const itemHtml = isLast
                    ? `<span class="breadcrumb-current">${item.name}</span>`
                    : `<span class="breadcrumb-item" onclick="navigateTo(${index})">${item.name}</span>`;

                return index === 0
                    ? itemHtml
                    : `<span class="breadcrumb-separator">›</span>${itemHtml}`;
            }).join('');
        }

        // Update pagination controls
        function updatePagination() {
            const pagination = document.getElementById('pagination');
            const info = document.getElementById('paginationInfo');
            const loadMoreBtn = document.getElementById('loadMoreBtn');

            const loaded = allMedia.length;
            const hasMore = loaded < totalRecordCount;

            if (totalRecordCount > pageSize) {
                pagination.style.display = 'block';
                info.textContent = `Showing ${loaded} of ${totalRecordCount} items`;
                loadMoreBtn.style.display = hasMore ? 'inline-block' : 'none';
            } else {
                pagination.style.display = 'none';
            }
        }

        // Load more items
        function loadMore() {
            startIndex += pageSize;
            loadItems(currentParentId, false);
        }

        // Handle sort option changes
        function onSortChange() {
            if (currentParentId) {
                loadItems(currentParentId, true); // Reset and reload with new sort
            }
        }

        // Search functionality
        document.getElementById('mediaSearch').addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const filtered = allMedia.filter(item =>
                (item.Name || '').toLowerCase().includes(searchTerm) ||
                (item.SeriesName || '').toLowerCase().includes(searchTerm)
            );
            renderMediaGrid(filtered);
        });

        // Render media grid
        function renderMediaGrid(items) {
            const grid = document.getElementById('mediaGrid');

            if (items.length === 0) {
                grid.innerHTML = '<div class="loading">No items found</div>';
                return;
            }

            grid.innerHTML = items.map(item => {
                const isBrowsable = item.Type === 'Series' || item.Type === 'Season';
                const isSelectable = item.Type === 'Episode' || item.Type === 'Movie';

                const posterUrl = item.ImageTags?.Primary
                    ? `<?php echo rtrim(getenv('JELLYFIN_URL') ?: '', '/'); ?>/Items/${item.Id}/Images/Primary?maxHeight=300&quality=90`
                    : '';

                const duration = item.RunTimeTicks
                    ? Math.round(item.RunTimeTicks / 10000000 / 60) // Convert to minutes
                    : 0;

                let badge = '';
                if (isBrowsable) {
                    badge = '<span class="browse-badge">→</span>';
                }

                const onClick = isBrowsable
                    ? `navigateInto(${JSON.stringify(item).replace(/'/g, "&apos;")})`
                    : (isSelectable ? `selectMedia(${JSON.stringify(item).replace(/'/g, "&apos;")})` : '');

                return `
                    <div class="media-item ${isBrowsable ? 'browsable' : ''}" onclick='${onClick}'>
                        ${badge}
                        ${posterUrl ? `<img class="media-poster" src="${posterUrl}" alt="${item.Name}">` : '<div class="media-poster"></div>'}
                        <div class="media-title" title="${item.Name}">${item.Name}</div>
                        <div class="media-type">${item.Type}</div>
                        ${duration > 0 ? `<div class="media-duration">${duration} min</div>` : ''}
                        ${item.IndexNumber ? `<div class="media-type">Ep ${item.IndexNumber}</div>` : ''}
                    </div>
                `;
            }).join('');
        }

        // Select media item
        function selectMedia(item) {
            selectedMedia = item;
            document.getElementById('selectedMediaInfo').classList.add('show');

            let title = item.Name;
            if (item.SeriesName) {
                title = `${item.SeriesName} - ${item.Name}`;
            }
            document.getElementById('selectedMediaTitle').textContent = title;

            // Set default time to now
            const now = new Date();
            now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
            document.getElementById('schedule_time').value = now.toISOString().slice(0, 16);

            // Highlight selected item
            document.querySelectorAll('.media-item').forEach(el => el.classList.remove('selected'));
            event.currentTarget.classList.add('selected');
        }

        // Clear selection
        function clearSelection() {
            selectedMedia = null;
            document.getElementById('selectedMediaInfo').classList.remove('show');
            document.querySelectorAll('.media-item').forEach(el => el.classList.remove('selected'));
        }

        // Add to schedule
        async function addToSchedule() {
            if (!selectedMedia) return;

            const streamId = <?php echo $stream_id ?? 'null'; ?>;
            if (!streamId) {
                alert('Please save the stream first before adding schedule items');
                return;
            }

            const scheduledTime = document.getElementById('schedule_time').value;
            if (!scheduledTime) {
                alert('Please select a time');
                return;
            }

            const duration = selectedMedia.RunTimeTicks
                ? Math.round(selectedMedia.RunTimeTicks / 10000000) // Convert to seconds
                : 3600; // Default 1 hour

            const metadata = JSON.stringify({
                type: selectedMedia.Type,
                seriesName: selectedMedia.SeriesName,
                seasonName: selectedMedia.SeasonName,
                indexNumber: selectedMedia.IndexNumber,
                parentIndexNumber: selectedMedia.ParentIndexNumber
            });

            try {
                const response = await fetch('<?php echo API_BASE_URL; ?>/schedules/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        stream_id: streamId,
                        title: selectedMedia.Name,
                        media_item_id: selectedMedia.Id,
                        scheduled_time: new Date(scheduledTime).toISOString(),
                        duration: duration,
                        metadata: metadata
                    })
                });

                const result = await response.json();

                if (response.ok) {
                    loadSchedules();
                    clearSelection();
                } else {
                    alert('Error adding to schedule: ' + (result.detail || 'Unknown error'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error adding to schedule');
            }
        }

        // Load schedules
        async function loadSchedules() {
            const streamId = <?php echo $stream_id ?? 'null'; ?>;
            if (!streamId) return;

            try {
                const response = await fetch(`<?php echo API_BASE_URL; ?>/schedules/stream/${streamId}`);
                schedules = await response.json();
                renderSchedules();
            } catch (error) {
                console.error('Error loading schedules:', error);
            }
        }

        // Render schedules
        function renderSchedules() {
            const list = document.getElementById('scheduleList');
            const count = document.getElementById('scheduleCount');

            count.textContent = `${schedules.length} item${schedules.length !== 1 ? 's' : ''} scheduled`;

            if (schedules.length === 0) {
                list.innerHTML = `
                    <div class="empty-schedule">
                        <p>📺 No items scheduled yet</p>
                        <p style="font-size: 14px; color: #666;">Browse Jellyfin content below to add items to your schedule</p>
                    </div>
                `;
                return;
            }

            // Sort by scheduled time
            schedules.sort((a, b) => new Date(a.scheduled_time) - new Date(b.scheduled_time));

            list.innerHTML = schedules.map(schedule => {
                const time = new Date(schedule.scheduled_time);
                const metadata = schedule.metadata ? JSON.parse(schedule.metadata) : {};
                const type = (metadata.type || 'Unknown').toLowerCase();
                const duration = Math.round(schedule.duration / 60); // Convert to minutes

                return `
                    <div class="schedule-item ${type}">
                        <div class="schedule-info">
                            <div class="schedule-time">${time.toLocaleString()}</div>
                            <div class="schedule-title">${schedule.title}</div>
                            <div class="schedule-meta">
                                ${type.toUpperCase()} • ${duration} min
                                ${metadata.seriesName ? ` • ${metadata.seriesName}` : ''}
                                ${metadata.seasonName ? ` • ${metadata.seasonName}` : ''}
                                ${metadata.indexNumber ? ` • Ep ${metadata.indexNumber}` : ''}
                            </div>
                        </div>
                        <div class="schedule-actions">
                            <button class="btn btn-danger btn-sm" onclick="deleteSchedule(${schedule.id})">Delete</button>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Delete schedule
        async function deleteSchedule(id) {
            if (!confirm('Delete this schedule item?')) return;

            try {
                const response = await fetch(`<?php echo API_BASE_URL; ?>/schedules/${id}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    loadSchedules();
                } else {
                    alert('Error deleting schedule');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error deleting schedule');
            }
        }

        // Handle stream form submission
        document.getElementById('streamForm').addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const streamId = formData.get('stream_id');
            const isEdit = streamId && streamId !== '';

            const data = {
                name: formData.get('name'),
                description: formData.get('description'),
                jellyfin_library_id: formData.get('jellyfin_library_id')
            };

            try {
                const url = isEdit
                    ? `<?php echo API_BASE_URL; ?>/streams/${streamId}`
                    : `<?php echo API_BASE_URL; ?>/streams/`;

                const method = isEdit ? 'PUT' : 'POST';

                const response = await fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: new URLSearchParams(data)
                });

                const result = await response.json();

                if (response.ok) {
                    if (!isEdit && result.id) {
                        window.location.href = `stream_edit_enhanced.php?id=${result.id}`;
                    } else {
                        alert('Stream saved successfully!');
                    }
                } else {
                    alert('Error saving stream: ' + (result.detail || 'Unknown error'));
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error saving stream');
            }
        });

        // Initial render
        renderSchedules();
    </script>
</body>
</html>
