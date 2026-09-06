import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'crowdcare.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(os.path.dirname(DB_PATH)):
        os.makedirs(os.path.dirname(DB_PATH))
        
    conn = get_db_connection()
    c = conn.cursor()
    
    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            status TEXT DEFAULT 'NORMAL'
        );

        CREATE TABLE IF NOT EXISTS cameras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id INTEGER,
            camera_name TEXT,
            FOREIGN KEY(zone_id) REFERENCES zones(id)
        );

        CREATE TABLE IF NOT EXISTS crowd_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            zone_id INTEGER,
            crowd_count INTEGER,
            density TEXT,
            latitude REAL,
            longitude REAL,
            incident_count INTEGER DEFAULT 0,
            response_time REAL DEFAULT 0,
            FOREIGN KEY(zone_id) REFERENCES zones(id)
        );

        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            incident_type TEXT NOT NULL,
            description TEXT,
            severity TEXT,
            latitude REAL,
            longitude REAL,
            status TEXT DEFAULT 'OPEN'
        );

        CREATE TABLE IF NOT EXISTS responders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            phone TEXT,
            latitude REAL,
            longitude REAL,
            status TEXT DEFAULT 'AVAILABLE',
            assigned_incident_id INTEGER,
            FOREIGN KEY(assigned_incident_id) REFERENCES incidents(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS analytics_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            metric_name TEXT,
            metric_value REAL
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            action TEXT
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            sender_name TEXT,
            role TEXT,
            message TEXT
        );
    ''')
    
    # Safely migrate existing databases to add user_id column if it doesn't exist
    try:
        c.execute('ALTER TABLE responders ADD COLUMN user_id INTEGER REFERENCES users(id)')
    except sqlite3.OperationalError:
        # Column already exists
        pass
        
    # Insert sample users
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        c.executemany('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', [
            ('admin', 'admin123', 'ADMIN'),
            ('marshal', 'marshal123', 'MARSHAL'),
            ('responder', 'responder123', 'RESPONDER')
        ])
    
    # Insert sample event
    c.execute('SELECT COUNT(*) FROM events')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO events (name, location, start_date, end_date) VALUES (?, ?, ?, ?)',
                  ('College Fest 2026', 'Main Campus', '2026-10-01', '2026-10-03'))
        
    # Insert sample responders
    c.execute('SELECT COUNT(*) FROM responders')
    if c.fetchone()[0] == 0:
        # Create users first
        c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", ('johndoe', 'password123', 'RESPONDER'))
        c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", ('janesmith', 'password123', 'RESPONDER'))
        
        user1 = c.execute("SELECT id FROM users WHERE username='johndoe'").fetchone()
        user2 = c.execute("SELECT id FROM users WHERE username='janesmith'").fetchone()
        
        c.executemany('INSERT INTO responders (name, phone, latitude, longitude, user_id) VALUES (?, ?, ?, ?, ?)', [
            ('John Doe', '1234567890', 13.0827, 80.2707, user1[0] if user1 else None),
            ('Jane Smith', '0987654321', 13.0830, 80.2710, user2[0] if user2 else None)
        ])
        
    # Ensure at least one zone exists for camera uploads to work
    c.execute('SELECT COUNT(*) FROM zones')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO zones (id, name, latitude, longitude) VALUES (?, ?, ?, ?)',
                  (1, 'Main Camera Zone', 13.0827, 80.2707))
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
