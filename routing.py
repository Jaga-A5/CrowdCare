import math

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculates the great-circle distance between two points on the Earth surface.
    """
    R = 6371.0 # Radius of Earth in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance

def find_nearest_responder(incident_lat, incident_lon, responders):
    """
    Finds the nearest available responder to an incident.
    responders is a list of dictionaries with keys: id, latitude, longitude, status
    """
    nearest = None
    min_dist = float('inf')
    
    for r in responders:
        if r['status'] == 'AVAILABLE':
            dist = calculate_haversine_distance(incident_lat, incident_lon, r['latitude'], r['longitude'])
            if dist < min_dist:
                min_dist = dist
                nearest = r['id']
                
    return nearest, min_dist
