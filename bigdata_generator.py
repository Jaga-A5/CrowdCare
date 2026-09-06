import random
import datetime
import os
import sqlite3
import json
import pandas as pd
from database import get_db_connection

def generate_zones(num_zones=40):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if zones exist
    c.execute('SELECT COUNT(*) FROM zones')
    if c.fetchone()[0] == 0:
        base_lat = 13.0827
        base_lon = 80.2707
        
        for i in range(1, num_zones + 1):
            lat = base_lat + random.uniform(-0.01, 0.01)
            lon = base_lon + random.uniform(-0.01, 0.01)
            c.execute('INSERT INTO zones (name, latitude, longitude) VALUES (?, ?, ?)',
                      (f'Zone {i}', lat, lon))
            
        conn.commit()
    conn.close()

def determine_density(count):
    if count < 200: return 'LOW'
    elif count < 500: return 'MEDIUM'
    elif count < 800: return 'HIGH'
    else: return 'CRITICAL'

def generate_big_data(num_records):
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('SELECT id, latitude, longitude FROM zones')
    zones = c.fetchall()
    
    if not zones:
        generate_zones()
        c.execute('SELECT id, latitude, longitude FROM zones')
        zones = c.fetchall()
        
    records = []
    base_time = datetime.datetime.now() - datetime.timedelta(days=7)
    
    for i in range(num_records):
        zone = random.choice(zones)
        zone_id = zone['id']
        lat = zone['latitude']
        lon = zone['longitude']
        
        # Time distribution (simulate peak hours)
        time_offset = random.randint(0, 7*24*60*60) # Random time in last 7 days
        record_time = base_time + datetime.timedelta(seconds=time_offset)
        
        # Simulate crowd based on time of day (peak at 18:00)
        hour = record_time.hour
        base_crowd = random.randint(50, 300)
        if 16 <= hour <= 20:
            base_crowd += random.randint(200, 600)
        
        crowd_count = base_crowd
        density = determine_density(crowd_count)
        
        incident_count = random.randint(0, 2) if density in ['HIGH', 'CRITICAL'] else 0
        response_time = random.uniform(2.0, 15.0) if incident_count > 0 else 0.0
        
        records.append((
            record_time.strftime("%Y-%m-%d %H:%M:%S"),
            zone_id,
            crowd_count,
            density,
            lat,
            lon,
            incident_count,
            response_time
        ))
    
    # Bulk insert for speed
    c.executemany('''
        INSERT INTO crowd_data 
        (timestamp, zone_id, crowd_count, density, latitude, longitude, incident_count, response_time) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', records)
    
    conn.commit()
    
    # Also save a sample to cloud storage simulation
    df = pd.DataFrame(records, columns=['timestamp', 'zone_id', 'crowd_count', 'density', 'latitude', 'longitude', 'incident_count', 'response_time'])
    cloud_path = os.path.join(os.path.dirname(__file__), 'cloud_storage', 'crowd_data', f'batch_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.csv')
    df.to_csv(cloud_path, index=False)
    
    conn.close()
    return True
