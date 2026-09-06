import pandas as pd
import numpy as np
from database import get_db_connection
import os
import sqlite3
import datetime
import random

def get_analytics():
    conn = get_db_connection()
    # Read crowd data into pandas dataframe
    query = "SELECT * FROM crowd_data"
    df = pd.read_sql_query(query, conn)
    
    # Read incidents data
    incidents_query = "SELECT * FROM incidents"
    df_incidents = pd.read_sql_query(incidents_query, conn)
    conn.close()
    
    analytics_results = {}
    
    if not df.empty:
        # Calculate statistics
        analytics_results['avg_crowd'] = round(df['crowd_count'].mean(), 2)
        analytics_results['max_crowd'] = int(df['crowd_count'].max())
        analytics_results['min_crowd'] = int(df['crowd_count'].min())
        
        # Convert timestamp to datetime if not already
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Peak crowd hour
        df['hour'] = df['timestamp'].dt.hour
        hourly_crowd = df.groupby('hour')['crowd_count'].mean()
        if not hourly_crowd.empty:
            peak_hour = hourly_crowd.idxmax()
            analytics_results['peak_hour'] = f"{peak_hour:02d}:00"
        else:
            analytics_results['peak_hour'] = "N/A"
            
        # Highest and lowest density zones
        zone_crowd = df.groupby('zone_id')['crowd_count'].mean()
        if not zone_crowd.empty:
            analytics_results['highest_density_zone'] = int(zone_crowd.idxmax())
            analytics_results['lowest_density_zone'] = int(zone_crowd.idxmin())
            
            # Zone wise comparison for charts
            analytics_results['zone_comparison'] = {
                'labels': [f"Zone {z}" for z in zone_crowd.index.tolist()[:10]], # Top 10
                'data': zone_crowd.values.tolist()[:10]
            }
        
        # Average response time
        avg_resp = df['response_time'].mean()
        analytics_results['avg_response_time'] = round(avg_resp, 2) if pd.notna(avg_resp) else 0.0
        
        # Density distribution
        density_counts = df['density'].value_counts()
        analytics_results['density_distribution'] = {
            'labels': density_counts.index.tolist(),
            'data': density_counts.values.tolist()
        }
        
        # Trend over time (last 10 records aggregated)
        recent = df.sort_values('timestamp').tail(100)
        time_trend = recent.groupby('timestamp')['crowd_count'].mean()
        analytics_results['time_trend'] = {
            'labels': [t.strftime("%H:%M:%S") for t in time_trend.index.tolist()],
            'data': time_trend.values.tolist()
        }
    else:
        # Default empty values
        analytics_results = {
            'avg_crowd': 0, 'max_crowd': 0, 'min_crowd': 0,
            'peak_hour': 'N/A', 'highest_density_zone': 'N/A', 'lowest_density_zone': 'N/A',
            'avg_response_time': 0, 'zone_comparison': {'labels': [], 'data': []},
            'density_distribution': {'labels': [], 'data': []},
            'time_trend': {'labels': [], 'data': []}
        }
        
    analytics_results['total_incidents'] = len(df_incidents) if not df_incidents.empty else 0
    
    return analytics_results

def predict_crowd(current_crowd):
    """
    Real Prediction Feature based on historical moving average.
    """
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT crowd_count FROM crowd_data ORDER BY timestamp DESC LIMIT 5", conn)
    conn.close()
    
    if df.empty or len(df) < 2:
        predicted_crowd = current_crowd
    else:
        # Simple moving average of the last 5 real camera captures
        predicted_crowd = int(df['crowd_count'].mean())
    
    # Use realistic thresholds matching the camera (e.g. 5-10 people)
    if predicted_crowd < 3:
        prediction = 'LOW'
    elif predicted_crowd < 6:
        prediction = 'MEDIUM'
    elif predicted_crowd < 10:
        prediction = 'HIGH'
    else:
        prediction = 'CRITICAL'
        
    return predicted_crowd, prediction
