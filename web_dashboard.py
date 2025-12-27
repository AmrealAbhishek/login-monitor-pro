#!/usr/bin/env python3
"""
Web Dashboard for Login Monitor PRO
====================================

A beautiful web interface to:
- View all login events
- Browse captured images
- View locations on a map
- Manage settings
- Add known faces
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

try:
    from flask import Flask, render_template_string, jsonify, request, send_file, redirect, url_for
except ImportError:
    print("Flask not installed. Run: pip3 install flask")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
EVENTS_DIR = SCRIPT_DIR / "events"
IMAGES_DIR = SCRIPT_DIR / "captured_images"
FACES_DIR = SCRIPT_DIR / "known_faces"
CONFIG_FILE = SCRIPT_DIR / "config.json"

app = Flask(__name__)

# HTML Template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login Monitor PRO - Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body { background: #1a1a2e; color: #eee; }
        .navbar { background: #16213e !important; }
        .card { background: #16213e; border: 1px solid #0f3460; }
        .card-header { background: #0f3460; border-bottom: 1px solid #0f3460; }
        .table { color: #eee; }
        .table-dark { background: #16213e; }
        .event-card { transition: transform 0.2s; cursor: pointer; }
        .event-card:hover { transform: scale(1.02); }
        .status-sent { color: #00ff88; }
        .status-pending { color: #ffaa00; }
        .thumbnail { width: 100px; height: 75px; object-fit: cover; border-radius: 5px; }
        .event-type-login { border-left: 4px solid #00ff88; }
        .event-type-unlock { border-left: 4px solid #00aaff; }
        .event-type-wake { border-left: 4px solid #ffaa00; }
        .map-container { height: 400px; border-radius: 10px; overflow: hidden; }
        .stats-card { background: linear-gradient(135deg, #0f3460 0%, #16213e 100%); }
        .stats-number { font-size: 2.5rem; font-weight: bold; }
        #map { height: 100%; width: 100%; }
        .face-thumbnail { width: 100px; height: 100px; object-fit: cover; border-radius: 50%; }
        .modal-content { background: #16213e; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark navbar-expand-lg">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="bi bi-shield-lock"></i> Login Monitor PRO
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/"><i class="bi bi-speedometer2"></i> Dashboard</a>
                <a class="nav-link" href="/events"><i class="bi bi-list-ul"></i> Events</a>
                <a class="nav-link" href="/map"><i class="bi bi-geo-alt"></i> Map</a>
                <a class="nav-link" href="/faces"><i class="bi bi-people"></i> Faces</a>
                <a class="nav-link" href="/settings"><i class="bi bi-gear"></i> Settings</a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% block content %}{% endblock %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
"""

INDEX_HTML = """
{% extends "base" %}
{% block content %}
<div class="row mb-4">
    <div class="col-md-3">
        <div class="card stats-card text-center p-3">
            <div class="stats-number text-primary">{{ stats.total }}</div>
            <div>Total Events</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card stats-card text-center p-3">
            <div class="stats-number text-success">{{ stats.today }}</div>
            <div>Today</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card stats-card text-center p-3">
            <div class="stats-number text-warning">{{ stats.week }}</div>
            <div>This Week</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card stats-card text-center p-3">
            <div class="stats-number text-info">{{ stats.images }}</div>
            <div>Photos</div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <i class="bi bi-clock-history"></i> Recent Events
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-dark table-hover">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Type</th>
                                <th>User</th>
                                <th>Location</th>
                                <th>Photo</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for event in events %}
                            <tr class="event-card event-type-{{ event.event_type|lower }}" onclick="showEvent('{{ event.id }}')">
                                <td>{{ event.timestamp }}</td>
                                <td><span class="badge bg-primary">{{ event.event_type }}</span></td>
                                <td>{{ event.user }}</td>
                                <td>
                                    {% if event.get('location') and event.location.get('city') %}
                                    <i class="bi bi-geo-alt"></i> {{ event.location.city }}
                                    {% else %}
                                    <i class="bi bi-geo-alt"></i> Unknown
                                    {% endif %}
                                </td>
                                <td>
                                    {% if event.photos %}
                                    <img src="/image/{{ event.photos[0] | basename }}" class="thumbnail" alt="capture">
                                    {% else %}
                                    <span class="text-muted">No photo</span>
                                    {% endif %}
                                </td>
                                <td>
                                    {% if event.status == 'sent' %}
                                    <span class="status-sent"><i class="bi bi-check-circle"></i></span>
                                    {% else %}
                                    <span class="status-pending"><i class="bi bi-clock"></i></span>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <div class="col-md-4">
        <div class="card mb-3">
            <div class="card-header">
                <i class="bi bi-geo-alt"></i> Last Known Location
            </div>
            <div class="card-body">
                <div class="map-container">
                    <div id="map"></div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <i class="bi bi-info-circle"></i> System Status
            </div>
            <div class="card-body">
                <p><i class="bi bi-check-circle text-success"></i> Monitor Active</p>
                <p><i class="bi bi-camera text-info"></i> Camera Ready</p>
                <p><i class="bi bi-telegram text-primary"></i> Telegram {{ 'Connected' if telegram_enabled else 'Not Configured' }}</p>
            </div>
        </div>
    </div>
</div>

<!-- Event Modal -->
<div class="modal fade" id="eventModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Event Details</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body" id="eventModalBody">
                Loading...
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script>
    var map = L.map('map').setView([{{ last_location.latitude or 0 }}, {{ last_location.longitude or 0 }}], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap'
    }).addTo(map);

    {% if last_location.latitude %}
    L.marker([{{ last_location.latitude }}, {{ last_location.longitude }}])
        .addTo(map)
        .bindPopup('Last known location');
    {% endif %}

    function showEvent(eventId) {
        fetch('/api/event/' + eventId)
            .then(response => response.json())
            .then(data => {
                let html = '<div class="row">';

                // Photos
                if (data.photos && data.photos.length > 0) {
                    html += '<div class="col-md-6">';
                    data.photos.forEach(photo => {
                        const filename = photo.split('/').pop();
                        html += '<img src="/image/' + filename + '" class="img-fluid mb-2 rounded">';
                    });
                    html += '</div>';
                }

                // Details
                html += '<div class="col-md-6">';
                html += '<h6><i class="bi bi-clock"></i> ' + data.timestamp + '</h6>';
                html += '<p><strong>Type:</strong> ' + data.event_type + '</p>';
                html += '<p><strong>User:</strong> ' + data.user + '</p>';
                html += '<p><strong>Host:</strong> ' + data.hostname + '</p>';
                html += '<p><strong>Public IP:</strong> ' + data.public_ip + '</p>';

                if (data.location) {
                    html += '<p><strong>Location:</strong><br>';
                    html += 'Lat: ' + (data.location.latitude || 'N/A') + '<br>';
                    html += 'Lon: ' + (data.location.longitude || 'N/A') + '<br>';
                    if (data.location.google_maps) {
                        html += '<a href="' + data.location.google_maps + '" target="_blank" class="btn btn-sm btn-primary mt-2"><i class="bi bi-geo-alt"></i> Open in Maps</a>';
                    }
                    html += '</p>';
                }

                if (data.battery && data.battery.available) {
                    html += '<p><strong>Battery:</strong> ' + data.battery.percentage + '%</p>';
                }

                if (data.wifi && data.wifi.available) {
                    html += '<p><strong>WiFi:</strong> ' + data.wifi.ssid + '</p>';
                }

                html += '</div></div>';

                document.getElementById('eventModalBody').innerHTML = html;
                new bootstrap.Modal(document.getElementById('eventModal')).show();
            });
    }
</script>
{% endblock %}
"""


def load_events():
    """Load all events from JSON files"""
    events = []
    if EVENTS_DIR.exists():
        for event_file in sorted(EVENTS_DIR.glob("*.json"), reverse=True):
            try:
                with open(event_file, 'r') as f:
                    event = json.load(f)
                    events.append(event)
            except:
                pass
    return events


def load_config():
    """Load configuration"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


@app.template_filter('basename')
def basename_filter(path):
    return os.path.basename(path) if path else ''


@app.route('/')
def index():
    events = load_events()[:20]  # Last 20 events
    config = load_config()

    # Calculate stats
    from datetime import datetime, timedelta
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)

    stats = {
        'total': len(load_events()),
        'today': len([e for e in events if e.get('timestamp', '').startswith(str(today))]),
        'week': len([e for e in load_events() if e.get('timestamp', '')[:10] >= str(week_ago)]),
        'images': len(list(IMAGES_DIR.glob("*.jpg"))) if IMAGES_DIR.exists() else 0
    }

    # Get last location
    last_location = {}
    for event in events:
        if event.get('location', {}).get('latitude'):
            last_location = event['location']
            break

    telegram_enabled = bool(config.get('telegram', {}).get('bot_token'))

    return render_template_string(
        DASHBOARD_HTML.replace('{% block content %}{% endblock %}', INDEX_HTML.split('{% block content %}')[1].split('{% endblock %}')[0])
            .replace('{% block scripts %}{% endblock %}', INDEX_HTML.split('{% block scripts %}')[1].split('{% endblock %}')[0]),
        events=events,
        stats=stats,
        last_location=last_location,
        telegram_enabled=telegram_enabled
    )


@app.route('/api/events')
def api_events():
    """API endpoint for events"""
    events = load_events()
    return jsonify(events)


@app.route('/api/event/<event_id>')
def api_event(event_id):
    """Get single event"""
    event_file = EVENTS_DIR / f"{event_id}.json"
    if event_file.exists():
        with open(event_file, 'r') as f:
            return jsonify(json.load(f))
    return jsonify({'error': 'Not found'}), 404


@app.route('/image/<filename>')
def serve_image(filename):
    """Serve captured images"""
    image_path = IMAGES_DIR / filename
    if image_path.exists():
        return send_file(str(image_path))
    return "Not found", 404


@app.route('/events')
def events_page():
    """Events list page"""
    events = load_events()
    html = """
    {% extends "base" %}
    {% block content %}
    <div class="card">
        <div class="card-header d-flex justify-content-between align-items-center">
            <span><i class="bi bi-list-ul"></i> All Events</span>
            <span class="badge bg-primary">{{ events|length }} total</span>
        </div>
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-dark table-hover">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Type</th>
                            <th>User</th>
                            <th>Public IP</th>
                            <th>Location</th>
                            <th>Photos</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for event in events %}
                        <tr>
                            <td>{{ event.timestamp }}</td>
                            <td><span class="badge bg-primary">{{ event.event_type }}</span></td>
                            <td>{{ event.user }}</td>
                            <td>{{ event.public_ip }}</td>
                            <td>{{ event.location.city if event.location else 'Unknown' }}</td>
                            <td>{{ event.photos|length if event.photos else 0 }}</td>
                            <td>
                                {% if event.status == 'sent' %}
                                <span class="text-success"><i class="bi bi-check-circle"></i> Sent</span>
                                {% else %}
                                <span class="text-warning"><i class="bi bi-clock"></i> Pending</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    {% endblock %}
    """
    return render_template_string(DASHBOARD_HTML.replace('{% block content %}{% endblock %}',
                                                          html.split('{% block content %}')[1].split('{% endblock %}')[0]),
                                  events=events)


@app.route('/map')
def map_page():
    """Map view with all locations"""
    events = load_events()
    locations = []
    for event in events:
        loc = event.get('location', {})
        if loc.get('latitude') and loc.get('longitude'):
            locations.append({
                'lat': loc['latitude'],
                'lon': loc['longitude'],
                'time': event.get('timestamp'),
                'type': event.get('event_type')
            })

    html = """
    {% extends "base" %}
    {% block content %}
    <div class="card">
        <div class="card-header">
            <i class="bi bi-geo-alt"></i> Location History
        </div>
        <div class="card-body">
            <div style="height: 600px;" id="fullmap"></div>
        </div>
    </div>
    {% endblock %}
    {% block scripts %}
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script>
        var map = L.map('fullmap').setView([0, 0], 2);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

        var locations = {{ locations|tojson }};
        var bounds = [];

        locations.forEach(function(loc) {
            var marker = L.marker([loc.lat, loc.lon]).addTo(map);
            marker.bindPopup('<b>' + loc.type + '</b><br>' + loc.time);
            bounds.push([loc.lat, loc.lon]);
        });

        if (bounds.length > 0) {
            map.fitBounds(bounds);
        }
    </script>
    {% endblock %}
    """

    return render_template_string(DASHBOARD_HTML.replace('{% block content %}{% endblock %}',
                                                          html.split('{% block content %}')[1].split('{% endblock %}')[0])
                                  .replace('{% block scripts %}{% endblock %}',
                                           html.split('{% block scripts %}')[1].split('{% endblock %}')[0]),
                                  locations=locations)


def main():
    print("="*60)
    print("LOGIN MONITOR PRO - Web Dashboard")
    print("="*60)
    print("\nStarting web server...")
    print("Open http://localhost:3017 in your browser")
    print("Press Ctrl+C to stop\n")
    app.run(host='0.0.0.0', port=3017, debug=False)


if __name__ == '__main__':
    main()
