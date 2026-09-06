import base64
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, Response, jsonify, render_template
from flask_socketio import SocketIO, emit

# ----------------------------------------------------------------------
#  Global state shared between the video-processing thread and the server
# ----------------------------------------------------------------------
processed_frame = None          # latest annotated frame (bytes)
current_count = 0               # latest crowd count
ALERT_THRESHOLD = 10            # configurable
ALERT_COOLDOWN = 30             # seconds between successive alerts

_last_alert_time = 0

# ----------------------------------------------------------------------
#  Flask app & SocketIO
# ----------------------------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
socketio = SocketIO(app, async_mode="eventlet")

# ----------------------------------------------------------------------
#  Video-processing thread
# ----------------------------------------------------------------------
def video_worker():
    global processed_frame, current_count, _last_alert_time

    cap = cv2.VideoCapture(0)
    
    # Wait for camera to initialize
    time.sleep(2.0)
    
    # Import locally to avoid circular import issues
    from crowd_detection import process_frame
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Run crowd detection
        annotated, count = process_frame(frame)
        current_count = count

        # Encode frame for MJPEG streaming
        ret, buffer = cv2.imencode('.jpg', annotated)
        if ret:
            processed_frame = buffer.tobytes()

        # Alert logic
        now = time.time()
        if count >= ALERT_THRESHOLD and (now - _last_alert_time) > ALERT_COOLDOWN:
            socketio.emit('alert', {'message': f'⚠️ ALERT: Crowd count reached {count}!'})
            
            # Send to main cloud server (Render)
            try:
                import requests
                payload = {
                    'type': 'Overcrowding',
                    'description': f"Automated Alert from Local Monitor: CRITICAL crowd density detected ({count} people).",
                    'severity': 'CRITICAL',
                    'latitude': 13.0827,
                    'longitude': 80.2707
                }
                requests.post('https://crowdcare-2wzg.onrender.com/api/report_incident', json=payload, timeout=5)
            except Exception as e:
                print(f"Failed to sync with Render server: {e}")
                
            _last_alert_time = now

        # Small sleep to limit CPU usage
        time.sleep(0.03)

    cap.release()

# Start background thread
threading.Thread(target=video_worker, daemon=True).start()

# ----------------------------------------------------------------------
#  Routes
# ----------------------------------------------------------------------
def generate_mjpeg():
    """Yield multipart JPEG frames."""
    while True:
        if processed_frame is None:
            time.sleep(0.1)
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + processed_frame + b'\r\n')
        time.sleep(0.03)

@app.route('/video_feed')
def video_feed():
    return Response(generate_mjpeg(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/count')
def api_count():
    return jsonify({'crowd_count': current_count})

@app.route('/')
def index():
    return render_template('monitor.html', threshold=ALERT_THRESHOLD)

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connected', {'msg': 'connected'})

if __name__ == '__main__':
    print("Starting Live Monitor Server on port 5001...")
    socketio.run(app, host='0.0.0.0', port=5001, debug=False)
