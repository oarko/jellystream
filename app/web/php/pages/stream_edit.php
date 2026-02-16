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
            max-height: 600px;
            overflow-y: auto;
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
        }
        .media-item:hover {
            background: #444;
            transform: scale(1.05);
        }
        .media-item.selected {
            border: 2px solid #00A4DC;
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
        .schedule-controls {
            display: flex;
            gap: 10px;
            align-items: center;
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
        .schedule-item.series {
            border-left-color: #17a2b8;
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
                                        data-type="<?php echo htmlspecialchars($library['CollectionType'] ?? 'mixed'); ?>">
                                    <?php echo htmlspecialchars($library['Name']); ?>
                                    (<?php echo htmlspecialchars($library['CollectionType'] ?? 'mixed'); ?>)
                                </option>
                            <?php endforeach; ?>
                        </select>
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
                </div>
            </div>
        </div>
    </div>

    <script>
        let selectedMedia = null;
        let schedules = <?php echo json_encode($schedules); ?>;
        let allMedia = [];

        // Load library items when library is selected
        document.getElementById('browse_library').addEventListener('change', async function() {
            const libraryId = this.value;
            if (!libraryId) {
                document.getElementById('mediaGrid').innerHTML = '<div class="loading">Select a library to browse content</div>';
                return;
            }

            document.getElementById('mediaGrid').innerHTML = '<div class="loading">Loading...</div>';

            try {
                const response = await fetch(`<?php echo API_BASE_URL; ?>/jellyfin/items/${libraryId}`);
                const data = await response.json();

                if (data.items && data.items.Items) {
                    allMedia = data.items.Items;
                    console.log('Loaded media items:', allMedia);
                    renderMediaGrid(allMedia);
                } else {
                    document.getElementById('mediaGrid').innerHTML = '<div class="loading">No items found</div>';
                }
            } catch (error) {
                console.error('Error loading library items:', error);
                document.getElementById('mediaGrid').innerHTML = '<div class="loading">Error loading items</div>';
            }
        });

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
                const posterUrl = item.ImageTags?.Primary
                    ? `<?php echo rtrim(getenv('JELLYFIN_URL') ?: '', '/'); ?>/Items/${item.Id}/Images/Primary?maxHeight=300&quality=90`
                    : '';

                const duration = item.RunTimeTicks
                    ? Math.round(item.RunTimeTicks / 10000000 / 60) // Convert to minutes
                    : 0;

                return `
                    <div class="media-item" onclick='selectMedia(${JSON.stringify(item)})'>
                        ${posterUrl ? `<img class="media-poster" src="${posterUrl}" alt="${item.Name}">` : '<div class="media-poster"></div>'}
                        <div class="media-title" title="${item.Name}">${item.Name}</div>
                        <div class="media-type">${item.Type}</div>
                        ${duration > 0 ? `<div class="media-duration">${duration} min</div>` : ''}
                    </div>
                `;
            }).join('');
        }

        // Select media item
        function selectMedia(item) {
            selectedMedia = item;
            document.getElementById('selectedMediaInfo').classList.add('show');
            document.getElementById('selectedMediaTitle').textContent = item.Name;

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
                    // Reload schedules
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
                        // Redirect to edit page with new stream ID
                        window.location.href = `stream_edit.php?id=${result.id}`;
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
