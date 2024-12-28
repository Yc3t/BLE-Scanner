from flask import Flask, render_template, jsonify
from pymongo import MongoClient
from datetime import datetime, timedelta
import argparse
import socket

app = Flask(__name__)

# Configuración MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client.tracking_data
collection = db.combined_data3

@app.route('/')
def index():
    """Página principal con el mapa"""
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    """API endpoint para obtener los últimos datos"""
    # Obtener datos de los últimos 5 minutos
    time_threshold = datetime.now() - timedelta(minutes=5)
    
    data = list(collection.find(
        {"timestamp": {"$gte": time_threshold}},
        {'_id': 0}
    ).sort('timestamp', -1).limit(100))
    
    # Estadísticas
    stats = {
        'total_buffers': collection.count_documents({}),
        'recent_buffers': len(data),
        'unique_devices': len({
            device['mac']
            for record in data
            for device in record.get('devices', [])
        }),
        'total_advertisements': sum(
            record['n_adv_raw']
            for record in data
            if 'n_adv_raw' in record
        ),
        'last_sequence': data[0]['sequence'] if data else None,
        'last_timestamp': data[0]['timestamp'] if data else None,
    }
    
    # Convertir a GeoJSON
    features = []
    
    for record in data:
        if record.get('gps_data') and record['gps_data'].get('coordinates'):
            # Crear feature para el punto GPS
            gps_feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        record['gps_data']['coordinates']['longitude'],
                        record['gps_data']['coordinates']['latitude']
                    ]
                },
                "properties": {
                    "timestamp": record['timestamp'],
                    "speed": record['gps_data'].get('speed', 0),
                    "type": "gps"
                }
            }
            features.append(gps_feature)
            
            # Crear features para cada dispositivo BLE
            for device in record.get('devices', []):
                ble_feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            record['gps_data']['coordinates']['longitude'],
                            record['gps_data']['coordinates']['latitude']
                        ]
                    },
                    "properties": {
                        "mac": device['mac'],
                        "rssi": device['rssi'],
                        "type": "ble",
                        "timestamp": record['timestamp']
                    }
                }
                features.append(ble_feature)
    
    return jsonify({
        "geojson": {
            "type": "FeatureCollection",
            "features": features
        },
        "stats": stats
    })

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Flask BLE GPS Tracker Server')
    parser.add_argument(
        '--host', 
        type=str, 
        default='0.0.0.0',  # Escucha en todas las interfaces
        help='Host address to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port', 
        type=int, 
        default=5000,
        help='Port to bind to (default: 5000)'
    )
    
    args = parser.parse_args()
    
    print(f"\nServidor iniciado!")
    print(f"Para acceder desde dispositivos en la red local:")
    
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"1. Usando IP local: http://{local_ip}:{args.port}")
    print(f"2. Usando hostname: http://{hostname}:{args.port}")
    print("\nPresiona Ctrl+C para detener el servidor\n")
    
    app.run(
        host=args.host,
        port=args.port,
        debug=True
    )