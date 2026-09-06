
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
