import os

base_dir = r"D:\cloud computing\CrowdCare"
templates_dir = os.path.join(base_dir, "templates")
static_css = os.path.join(base_dir, "static", "css")
static_js = os.path.join(base_dir, "static", "js")

os.makedirs(templates_dir, exist_ok=True)
os.makedirs(static_css, exist_ok=True)
os.makedirs(static_js, exist_ok=True)

files = {}

files["base.html"] = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CrowdCare</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    {% block head %}{% endblock %}
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">CrowdCare</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    {% if session.get('role') == 'ADMIN' %}
                    <li class="nav-item"><a class="nav-link" href="/dashboard">Dashboard</a></li>
                    <li class="nav-item"><a class="nav-link" href="/events">Events</a></li>
                    <li class="nav-item"><a class="nav-link" href="/zones">Zones</a></li>
                    <li class="nav-item"><a class="nav-link" href="/incidents">Incidents</a></li>
                    <li class="nav-item"><a class="nav-link" href="/responders">Responders</a></li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="cloudDropdown" role="button" data-bs-toggle="dropdown">Cloud & Big Data</a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="/cloud">Cloud Storage Sim</a></li>
                            <li><a class="dropdown-item" href="/cloud-concepts">Cloud Concepts</a></li>
                            <li><a class="dropdown-item" href="/bigdata">Big Data Gen</a></li>
                            <li><a class="dropdown-item" href="/analytics">Analytics</a></li>
                            <li><a class="dropdown-item" href="/bigdata-concepts">Big Data Concepts</a></li>
                            <li><a class="dropdown-item" href="/simulation">Simulation</a></li>
                        </ul>
                    </li>
                    {% elif session.get('role') == 'MARSHAL' %}
                    <li class="nav-item"><a class="nav-link" href="/marshal">Marshal Dashboard</a></li>
                    {% elif session.get('role') == 'RESPONDER' %}
                    <li class="nav-item"><a class="nav-link" href="/responders">Responder Assignments</a></li>
                    {% endif %}
                </ul>
                <ul class="navbar-nav">
                    {% if session.get('user_id') %}
                    <li class="nav-item"><a class="nav-link" href="/logout">Logout ({{ session.get('username') }})</a></li>
                    {% else %}
                    <li class="nav-item"><a class="nav-link" href="/login">Login</a></li>
                    {% endif %}
                    <li class="nav-item"><a class="nav-link bg-primary text-white ms-2 rounded" href="/camera">Open Camera</a></li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% block content %}{% endblock %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
"""

files["login.html"] = """{% extends "base.html" %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-4">
        <div class="card mt-5 shadow">
            <div class="card-header bg-primary text-white text-center">
                <h4>CrowdCare Login</h4>
            </div>
            <div class="card-body">
                {% if error %}
                <div class="alert alert-danger">{{ error }}</div>
                {% endif %}
                <form method="POST">
                    <div class="mb-3">
                        <label>Username</label>
                        <input type="text" name="username" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label>Password</label>
                        <input type="password" name="password" class="form-control" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Login</button>
                </form>
                <hr>
                <small class="text-muted">Hint: admin/admin123, marshal/marshal123, responder/responder123</small>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

files["dashboard.html"] = """{% extends "base.html" %}
{% block content %}
<h2>Admin Dashboard</h2>
<div class="row mb-4">
    <div class="col-md-3">
        <div class="card bg-info text-white text-center p-3 shadow-sm">
            <h5>Total Zones</h5>
            <h2 id="dash-zones">{{ zones }}</h2>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card bg-warning text-white text-center p-3 shadow-sm">
            <h5>Current Crowd</h5>
            <h2 id="dash-crowd">0</h2>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card bg-danger text-white text-center p-3 shadow-sm">
            <h5>Active Incidents</h5>
            <h2 id="dash-incidents">{{ incidents }}</h2>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card bg-success text-white text-center p-3 shadow-sm">
            <h5>Responders Available</h5>
            <h2 id="dash-responders">{{ responders }}</h2>
        </div>
    </div>
</div>

<div class="row mb-4">
    <div class="col-md-12">
        <div class="card shadow-sm">
            <div class="card-header bg-dark text-white">Live Crowd Map</div>
            <div class="card-body p-0">
                <div id="map" style="height: 400px; width: 100%;"></div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/app.js') }}"></script>
<script>
    document.addEventListener("DOMContentLoaded", function() {
        initMap();
        fetchDashboardData();
        setInterval(fetchDashboardData, 5000);
    });
</script>
{% endblock %}
"""

files["camera.html"] = """{% extends "base.html" %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card shadow">
            <div class="card-header bg-dark text-white">
                <h4>Mobile Crowd Monitoring</h4>
            </div>
            <div class="card-body text-center">
                <video id="video" width="100%" autoplay></video>
                <canvas id="canvas" style="display:none;"></canvas>
                <div class="mt-3">
                    <button id="captureBtn" class="btn btn-success">Capture & Upload</button>
                </div>
                <div id="result" class="mt-3 font-weight-bold" style="font-size: 1.2em;"></div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const captureBtn = document.getElementById('captureBtn');
    const resultDiv = document.getElementById('result');

    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
        .then(stream => { video.srcObject = stream; })
        .catch(err => { console.error("Error accessing camera: ", err); });

    captureBtn.addEventListener('click', () => {
        resultDiv.innerHTML = "Processing...";
        const context = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        canvas.toBlob(blob => {
            const formData = new FormData();
            formData.append('image', blob, 'capture.jpg');
            formData.append('zone_id', Math.floor(Math.random() * 40) + 1); // Random zone for demo
            
            fetch('/api/upload_image', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                let color = "green";
                if(data.density === "HIGH") color = "orange";
                if(data.density === "CRITICAL") color = "red";
                resultDiv.innerHTML = `<span style="color:${color}">Count: ${data.crowd_count} | Density: ${data.density}</span>`;
            })
            .catch(err => {
                resultDiv.innerHTML = "Error uploading image.";
            });
        }, 'image/jpeg');
    });
</script>
{% endblock %}
"""

files["analytics.html"] = """{% extends "base.html" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
    <h2>Big Data Analytics Dashboard</h2>
    <a href="/bigdata" class="btn btn-outline-primary">Generate More Data</a>
</div>

<div class="row mb-4 text-center">
    <div class="col-md-2">
        <div class="card p-2 bg-light"><h6>Avg Crowd</h6><h4>{{ analytics.avg_crowd }}</h4></div>
    </div>
    <div class="col-md-2">
        <div class="card p-2 bg-light"><h6>Max Crowd</h6><h4>{{ analytics.max_crowd }}</h4></div>
    </div>
    <div class="col-md-2">
        <div class="card p-2 bg-light"><h6>Peak Hour</h6><h4>{{ analytics.peak_hour }}</h4></div>
    </div>
    <div class="col-md-2">
        <div class="card p-2 bg-light"><h6>Avg Resp Time</h6><h4>{{ analytics.avg_response_time }}s</h4></div>
    </div>
    <div class="col-md-4">
        <div class="card p-2 bg-warning text-dark">
            <h6>Simple Crowd Prediction</h6>
            <span>Current: <b>{{ current_crowd }}</b> &rarr; Predicted: <b>{{ pred_val }} ({{ pred_cat }})</b></span>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-md-6 mb-4">
        <div class="card">
            <div class="card-header">Top 10 Crowded Zones</div>
            <div class="card-body"><canvas id="zoneChart"></canvas></div>
        </div>
    </div>
    <div class="col-md-6 mb-4">
        <div class="card">
            <div class="card-header">Density Distribution</div>
            <div class="card-body"><canvas id="densityChart"></canvas></div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    const analytics = {{ analytics|tojson }};
    
    // Zone Chart
    new Chart(document.getElementById('zoneChart'), {
        type: 'bar',
        data: {
            labels: analytics.zone_comparison.labels,
            datasets: [{
                label: 'Average Crowd Count',
                data: analytics.zone_comparison.data,
                backgroundColor: 'rgba(54, 162, 235, 0.5)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        }
    });

    // Density Chart
    new Chart(document.getElementById('densityChart'), {
        type: 'pie',
        data: {
            labels: analytics.density_distribution.labels,
            datasets: [{
                data: analytics.density_distribution.data,
                backgroundColor: ['#28a745', '#ffc107', '#fd7e14', '#dc3545']
            }]
        }
    });
</script>
{% endblock %}
"""

files["cloud.html"] = """{% extends "base.html" %}
{% block content %}
<div class="jumbotron bg-light p-5 rounded mt-3">
    <h1 class="display-4">Cloud Storage Simulation</h1>
    <p class="lead">This module demonstrates how data generated by mobile clients and IoT devices is stored in the cloud.</p>
    <hr class="my-4">
    <p>In a real deployment, this local storage layer would be replaced by Amazon S3, Azure Blob Storage, or Google Cloud Storage.</p>
    <a class="btn btn-info btn-lg" href="/cloud-concepts" role="button">Learn Cloud Concepts</a>
</div>

<div class="row mt-4">
    <div class="col-md-4">
        <div class="card text-center shadow-sm">
            <div class="card-header bg-primary text-white">Data Records</div>
            <div class="card-body"><h2>{{ stats.total_records }}</h2></div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card text-center shadow-sm">
            <div class="card-header bg-success text-white">Crowd Data Size</div>
            <div class="card-body"><h2>{{ "%.2f"|format(stats.crowd_data_size) }} KB</h2></div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card text-center shadow-sm">
            <div class="card-header bg-danger text-white">Incident Data Size</div>
            <div class="card-body"><h2>{{ "%.2f"|format(stats.incident_data_size) }} KB</h2></div>
        </div>
    </div>
</div>
{% endblock %}
"""

files["bigdata.html"] = """{% extends "base.html" %}
{% block content %}
<h2>Big Data Generation</h2>
<p>Simulate large volumes of data for analytics processing.</p>

<div class="card p-4 shadow-sm mb-4">
    <h4>Generate Crowd Records</h4>
    <div class="d-flex gap-3 mt-3">
        <button class="btn btn-outline-primary gen-btn" data-count="1000">Generate 1,000</button>
        <button class="btn btn-outline-primary gen-btn" data-count="10000">Generate 10,000</button>
        <button class="btn btn-outline-primary gen-btn" data-count="50000">Generate 50,000</button>
        <button class="btn btn-primary gen-btn" data-count="100000">Generate 100,000 (Stress Test)</button>
    </div>
    <div id="status" class="mt-3 text-success font-weight-bold"></div>
</div>

<a href="/analytics" class="btn btn-success">Go to Analytics</a>
{% endblock %}

{% block scripts %}
<script>
    document.querySelectorAll('.gen-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const count = e.target.getAttribute('data-count');
            const statusDiv = document.getElementById('status');
            statusDiv.innerHTML = `Generating ${count} records... Please wait.`;
            
            fetch('/api/generate_bigdata', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({count: count})
            })
            .then(res => res.json())
            .then(data => {
                statusDiv.innerHTML = data.message;
            });
        });
    });
</script>
{% endblock %}
"""

files["marshal.html"] = """{% extends "base.html" %}
{% block content %}
<h2>Marshal Interface: Report Incident</h2>
<div class="card shadow-sm mt-4">
    <div class="card-body">
        <form id="incidentForm">
            <div class="mb-3">
                <label>Incident Type</label>
                <select class="form-select" id="incType">
                    <option>Overcrowding</option>
                    <option>Medical Emergency</option>
                    <option>Fire</option>
                    <option>Security</option>
                    <option>Other</option>
                </select>
            </div>
            <div class="mb-3">
                <label>Severity</label>
                <select class="form-select" id="incSev">
                    <option>LOW</option>
                    <option>MEDIUM</option>
                    <option>HIGH</option>
                    <option>CRITICAL</option>
                </select>
            </div>
            <div class="mb-3">
                <label>Description</label>
                <textarea class="form-control" id="incDesc" rows="3"></textarea>
            </div>
            <button type="button" class="btn btn-danger" onclick="submitIncident()">Report Incident</button>
        </form>
        <div id="incResult" class="mt-3 font-weight-bold text-success"></div>
    </div>
</div>
{% endblock %}
{% block scripts %}
<script>
    function submitIncident() {
        const data = {
            type: document.getElementById('incType').value,
            severity: document.getElementById('incSev').value,
            description: document.getElementById('incDesc').value,
            latitude: 13.0827 + (Math.random() * 0.01),
            longitude: 80.2707 + (Math.random() * 0.01)
        };
        fetch('/api/report_incident', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        })
        .then(res => res.json())
        .then(res => {
            document.getElementById('incResult').innerHTML = res.message + ". Assigned to: " + res.assigned_responder;
            document.getElementById('incidentForm').reset();
        });
    }
</script>
{% endblock %}
"""

# Placeholder empty templates for routes that just render something simple
simple_templates = ['events', 'zones', 'incidents', 'responders', 'cloud_concepts', 'bigdata_concepts', 'simulation']
for t in simple_templates:
    files[f"{t}.html"] = f"{{% extends 'base.html' %}}\n{{% block content %}}\n<h2>{t.replace('_', ' ').title()}</h2>\n<p>This is the {t} page. Data can be viewed here.</p>\n{{% endblock %}}"

# static JS
files["../static/js/app.js"] = """
let map;
let markers = {};

function initMap() {
    map = L.map('map').setView([13.0827, 80.2707], 14);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
}

function fetchDashboardData() {
    fetch('/api/dashboard_data')
        .then(res => res.json())
        .then(data => {
            document.getElementById('dash-crowd').innerText = data.current_crowd;
            
            // Update map markers
            data.zones.forEach(zone => {
                let color = "blue";
                if(zone.status === 'MEDIUM') color = "yellow";
                if(zone.status === 'HIGH') color = "orange";
                if(zone.status === 'CRITICAL') color = "red";
                
                if(!markers[zone.id]) {
                    markers[zone.id] = L.circleMarker([zone.latitude, zone.longitude], {
                        radius: 8,
                        color: color,
                        fillColor: color,
                        fillOpacity: 0.7
                    }).addTo(map).bindPopup(zone.name + " - " + zone.status);
                } else {
                    markers[zone.id].setStyle({color: color, fillColor: color});
                    markers[zone.id].setPopupContent(zone.name + " - " + zone.status);
                }
            });
        });
}
"""

files["../static/css/style.css"] = """
body { background-color: #f8f9fa; }
.card { border-radius: 10px; }
"""

for filename, content in files.items():
    filepath = os.path.join(templates_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("All templates and static assets generated successfully.")
