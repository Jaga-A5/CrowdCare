from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from database import init_db, get_db_connection
from crowd_detection import estimate_crowd
from analytics import get_analytics, predict_crowd
from bigdata_generator import generate_zones, generate_big_data
from routing import find_nearest_responder
import os
import datetime

app = Flask(__name__)
app.secret_key = 'crowdcare_secret_key'

# Ensure database is initialized even when running via Gunicorn
init_db()

# Ensure upload directory exists
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Cloud Storage Simulation helper
def simulate_cloud_upload(data, category):
    import json
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filepath = os.path.join(os.path.dirname(__file__), 'cloud_storage', category, f'data_{timestamp}.json')
    with open(filepath, 'w') as f:
        json.dump(data, f)

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            if user['role'] == 'ADMIN':
                return redirect(url_for('dashboard'))
            elif user['role'] == 'MARSHAL':
                return redirect(url_for('marshal'))
            elif user['role'] == 'RESPONDER':
                return redirect(url_for('responders'))
                
        return render_template('login.html', error="Invalid credentials")
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session['role'] != 'ADMIN':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    zones = conn.execute('SELECT COUNT(*) FROM zones').fetchone()[0]
    incidents = conn.execute("SELECT COUNT(*) FROM incidents WHERE status='OPEN'").fetchone()[0]
    responders = conn.execute("SELECT COUNT(*) FROM responders WHERE status='AVAILABLE'").fetchone()[0]
    records = conn.execute("SELECT COUNT(*) FROM crowd_data").fetchone()[0]
    critical_zones = conn.execute("SELECT COUNT(*) FROM zones WHERE status='CRITICAL'").fetchone()[0]
    conn.close()
    
    return render_template('dashboard.html', 
                           zones=zones, 
                           incidents=incidents, 
                           responders=responders, 
                           records=records,
                           critical_zones=critical_zones)

@app.route('/api/dashboard_data')
def dashboard_data():
    conn = get_db_connection()
    # Get recent crowd data
    recent = conn.execute('SELECT crowd_count FROM crowd_data ORDER BY timestamp DESC LIMIT 1').fetchone()
    current_crowd = recent[0] if recent else 0
    
    # Get zones for map
    zones = [dict(row) for row in conn.execute('SELECT * FROM zones').fetchall()]
    
    # Get open incidents
    incidents = [dict(row) for row in conn.execute("SELECT * FROM incidents WHERE status='OPEN'").fetchall()]
    
    # Get responders
    responders = [dict(row) for row in conn.execute('SELECT * FROM responders').fetchall()]
    
    conn.close()
    
    return jsonify({
        'current_crowd': current_crowd,
        'zones': zones,
        'incidents': incidents,
        'responders': responders
    })

@app.route('/events')
def events():
    conn = get_db_connection()
    events_list = conn.execute('SELECT * FROM events').fetchall()
    conn.close()
    return render_template('events.html', events=events_list)

@app.route('/events/create', methods=['POST'])
def create_event():
    if 'user_id' not in session or session['role'] != 'ADMIN':
        return redirect(url_for('login'))
    
    name = request.form['name']
    location = request.form['location']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    
    conn = get_db_connection()
    conn.execute('INSERT INTO events (name, location, start_date, end_date) VALUES (?, ?, ?, ?)',
                 (name, location, start_date, end_date))
    conn.commit()
    conn.close()
    
    return redirect(url_for('events'))

@app.route('/zones')
def zones():
    conn = get_db_connection()
    zones_list = conn.execute('SELECT * FROM zones').fetchall()
    conn.close()
    return render_template('zones.html', zones=zones_list)

@app.route('/zones/create', methods=['POST'])
def create_zone():
    if 'user_id' not in session or session['role'] != 'ADMIN':
        return redirect(url_for('login'))
    
    name = request.form['name']
    latitude = float(request.form['latitude'])
    longitude = float(request.form['longitude'])
    
    conn = get_db_connection()
    conn.execute('INSERT INTO zones (name, latitude, longitude) VALUES (?, ?, ?)',
                 (name, latitude, longitude))
    conn.commit()
    conn.close()
    
    return redirect(url_for('zones'))

@app.route('/camera')
def camera():
    return render_template('camera.html')

@app.route('/api/upload_image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'})
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
        
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    
    # Get configuration from request
    threshold = int(request.form.get('threshold', 5))
    zone_id = request.form.get('zone_id', 1)
    
    # Process image with Prototype Crowd Estimation (OpenCV-based)
    crowd_count, density, annotated_img_base64 = estimate_crowd(filepath, threshold=threshold)
    
    # Save to db
    conn = get_db_connection()
    lat = request.form.get('latitude', 13.0827)
    lon = request.form.get('longitude', 80.2707)
    
    c = conn.cursor()
    c.execute('''INSERT INTO crowd_data (zone_id, crowd_count, density, latitude, longitude) 
                 VALUES (?, ?, ?, ?, ?)''', (zone_id, crowd_count, density, lat, lon))
                 
    # Update zone status
    c.execute("UPDATE zones SET status=? WHERE id=?", (density, zone_id))
    
    alert_message = ""
    assigned_name = ""
    
    # Automatic Alerting Logic
    if density in ['HIGH', 'CRITICAL']:
        # Check if there is already an OPEN incident near this zone (prevent alert flooding)
        existing_incident = c.execute("SELECT id FROM incidents WHERE status='OPEN' AND description LIKE ?", (f"%Zone {zone_id}%",)).fetchone()
        
        if not existing_incident:
            desc = f"Automated Alert: {density} crowd density detected in Zone {zone_id} ({crowd_count} people)."
            c.execute('''INSERT INTO incidents (incident_type, description, severity, latitude, longitude)
                         VALUES (?, ?, ?, ?, ?)''', 
                      ('Overcrowding', desc, density, lat, lon))
            incident_id = c.lastrowid
            
            # Find nearest responder
            responders = [dict(row) for row in c.execute('SELECT * FROM responders').fetchall()]
            nearest_id, dist = find_nearest_responder(lat, lon, responders)
            
            assigned_name = "None Available"
            if nearest_id:
                c.execute("UPDATE responders SET status='ASSIGNED', assigned_incident_id=? WHERE id=?", 
                          (incident_id, nearest_id))
                assigned_responder = c.execute("SELECT name FROM responders WHERE id=?", (nearest_id,)).fetchone()
                assigned_name = assigned_responder['name']
                
            alert_message = f"ALERT: Incident created. Responder {assigned_name} assigned."
        else:
            alert_message = f"WARNING: {density} crowd density. (Incident already open for this zone)."
        
    conn.commit()
    conn.close()
    
    # Simulate cloud storage
    simulate_cloud_upload({
        'zone_id': zone_id,
        'crowd_count': crowd_count,
        'density': density,
        'latitude': lat,
        'longitude': lon,
        'image': file.filename,
        'alert': alert_message
    }, 'crowd_data')
    
    return jsonify({
        'crowd_count': crowd_count,
        'density': density,
        'message': 'Image processed successfully',
        'alert_message': alert_message
    })

@app.route('/marshal')
def marshal():
    return render_template('marshal.html')

@app.route('/api/report_incident', methods=['POST'])
def report_incident():
    data = request.json
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Store incident
    c.execute('''INSERT INTO incidents (incident_type, description, severity, latitude, longitude)
                 VALUES (?, ?, ?, ?, ?)''', 
              (data['type'], data['description'], data['severity'], data['latitude'], data['longitude']))
    incident_id = c.lastrowid
    
    # Find nearest responder
    responders = [dict(row) for row in c.execute('SELECT * FROM responders').fetchall()]
    nearest_id, dist = find_nearest_responder(data['latitude'], data['longitude'], responders)
    
    assigned_name = "None Available"
    if nearest_id:
        c.execute("UPDATE responders SET status='ASSIGNED', assigned_incident_id=? WHERE id=?", 
                  (incident_id, nearest_id))
        assigned_responder = c.execute("SELECT name FROM responders WHERE id=?", (nearest_id,)).fetchone()
        assigned_name = assigned_responder['name']
        
    conn.commit()
    conn.close()
    
    simulate_cloud_upload(data, 'incident_data')
    
    return jsonify({
        'message': 'Incident reported successfully',
        'assigned_responder': assigned_name
    })

@app.route('/incidents')
def incidents():
    conn = get_db_connection()
    incs = conn.execute('SELECT * FROM incidents ORDER BY timestamp DESC').fetchall()
    conn.close()
    return render_template('incidents.html', incidents=incs)

@app.route('/incidents/resolve/<int:incident_id>', methods=['POST'])
def resolve_incident(incident_id):
    if 'user_id' not in session or session['role'] != 'ADMIN':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    # Update incident status
    conn.execute("UPDATE incidents SET status='RESOLVED' WHERE id=?", (incident_id,))
    # Reset assigned responder if any
    conn.execute("UPDATE responders SET status='AVAILABLE', assigned_incident_id=NULL WHERE assigned_incident_id=?", (incident_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('incidents'))

@app.route('/responders')
def responders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    # For Admin, show all responders
    if session['role'] == 'ADMIN':
        resps = conn.execute('''
            SELECT r.*, u.username 
            FROM responders r 
            LEFT JOIN users u ON r.user_id = u.id
        ''').fetchall()
        conn.close()
        return render_template('responders.html', responders=resps, role='ADMIN')
        
    # For Responder, show their specific dashboard
    elif session['role'] == 'RESPONDER':
        user_id = session['user_id']
        resp = conn.execute('SELECT * FROM responders WHERE user_id = ?', (user_id,)).fetchone()
        if not resp:
            # Fallback if responder profile not linked properly (e.g. sample accounts)
            resp = conn.execute("SELECT * FROM responders WHERE name LIKE ?", (f"%{session['username']}%",)).fetchone()
            if not resp:
                resp = conn.execute('SELECT * FROM responders LIMIT 1').fetchone() # Final fallback
                
        incident = None
        if resp and resp['assigned_incident_id']:
            incident = conn.execute('SELECT * FROM incidents WHERE id = ?', (resp['assigned_incident_id'],)).fetchone()
            
        conn.close()
        return render_template('responders.html', responder=resp, incident=incident, role='RESPONDER')
        
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/responders/create', methods=['POST'])
def create_responder():
    if 'user_id' not in session or session['role'] != 'ADMIN':
        return redirect(url_for('login'))
    
    name = request.form['name']
    phone = request.form['phone']
    latitude = float(request.form['latitude'])
    longitude = float(request.form['longitude'])
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Auto-generate a login for the responder
    base_username = name.lower().replace(' ', '')
    username = base_username
    # Ensure username is unique
    counter = 1
    while c.execute('SELECT 1 FROM users WHERE username = ?', (username,)).fetchone():
        username = f"{base_username}{counter}"
        counter += 1
        
    password = 'password123'
    c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
              (username, password, 'RESPONDER'))
    user_id = c.lastrowid
    
    c.execute('INSERT INTO responders (name, phone, latitude, longitude, user_id) VALUES (?, ?, ?, ?, ?)',
                 (name, phone, latitude, longitude, user_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('responders'))

@app.route('/responders/reset/<int:responder_id>', methods=['POST'])
def reset_responder(responder_id):
    if 'user_id' not in session or session['role'] != 'ADMIN':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    conn.execute("UPDATE responders SET status='AVAILABLE', assigned_incident_id=NULL WHERE id=?", (responder_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('responders'))

@app.route('/cloud')
def cloud():
    # Gather stats for simulated cloud storage
    import glob
    def get_dir_size(path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size

    cloud_base = os.path.join(os.path.dirname(__file__), 'cloud_storage')
    crowd_size = get_dir_size(os.path.join(cloud_base, 'crowd_data'))
    incident_size = get_dir_size(os.path.join(cloud_base, 'incident_data'))
    
    conn = get_db_connection()
    records = conn.execute("SELECT COUNT(*) FROM crowd_data").fetchone()[0]
    conn.close()
    
    stats = {
        'total_records': records,
        'crowd_data_size': crowd_size / 1024, # KB
        'incident_data_size': incident_size / 1024,
        'total_size': (crowd_size + incident_size) / 1024
    }
    
    return render_template('cloud.html', stats=stats)

@app.route('/cloud-concepts')
def cloud_concepts():
    return render_template('cloud_concepts.html')

@app.route('/bigdata')
def bigdata():
    return render_template('bigdata.html')

@app.route('/api/generate_bigdata', methods=['POST'])
def generate_data_api():
    return jsonify({'message': 'Fake data generation disabled for production.'}), 403

@app.route('/bigdata-concepts')
def bigdata_concepts():
    return render_template('bigdata_concepts.html')

@app.route('/analytics')
def analytics_page():
    results = get_analytics()
    # Simple prediction demo
    conn = get_db_connection()
    recent = conn.execute('SELECT crowd_count FROM crowd_data ORDER BY timestamp DESC LIMIT 1').fetchone()
    current_crowd = recent[0] if recent else 0
    conn.close()
    
    pred_val, pred_cat = predict_crowd(current_crowd)
    
    return render_template('analytics.html', analytics=results, current_crowd=current_crowd, pred_val=pred_val, pred_cat=pred_cat)

@app.route('/api/analytics_data')
def api_analytics_data():
    return jsonify(get_analytics())

@app.route('/simulation')
def simulation():
    return render_template('simulation.html')

@app.route('/api/generate_zones', methods=['POST'])
def api_generate_zones():
    return jsonify({'message': 'Fake zone generation disabled for production.'}), 403

# Chat functionality
@app.route('/api/chat/messages')
def get_chat_messages():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    messages = [dict(row) for row in conn.execute('SELECT * FROM messages ORDER BY timestamp ASC').fetchall()]
    conn.close()
    return jsonify(messages)

@app.route('/api/chat/send', methods=['POST'])
def send_chat_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'error': 'Message cannot be empty'}), 400
        
    sender_name = session.get('username')
    role = session.get('role')
    
    conn = get_db_connection()
    conn.execute('INSERT INTO messages (sender_name, role, message) VALUES (?, ?, ?)',
                 (sender_name, role, message))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
