from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient
from datetime import datetime, timedelta
from flask_compress import Compress  # Para comprimir respuestas

app = Flask(__name__)
Compress(app)  # Habilitar compresión

# Configuración MongoDB con índices
client = MongoClient('mongodb://localhost:27017/')
db = client.tracking_data
collection = db.combined_data3

# Crear índices para mejorar el rendimiento
collection.create_index([("timestamp", -1)])
collection.create_index([("sequence", 1)])

@app.route('/')
def index():
    """Página principal con el mapa"""
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    """API endpoint optimizado con rango de tiempo configurable"""
    try:
        time_range = request.args.get('timeRange', '5m')
        print(f"Requested time range: {time_range}")
        
        try:
            value = int(time_range[:-1])
            unit = time_range[-1].lower()
            
            if unit == 'm':
                delta = timedelta(minutes=value)
            elif unit == 'h':
                delta = timedelta(hours=value)
            elif unit == 'd':
                delta = timedelta(days=value)
            else:
                delta = timedelta(minutes=5)
        except:
            delta = timedelta(minutes=5)
        
        time_threshold = datetime.utcnow() - delta
        print(f"Looking for data since: {time_threshold}")

        # Query MongoDB with error handling
        try:
            data = list(collection.find(
                {"timestamp": {"$gte": time_threshold}},
                {
                    '_id': 0,
                    'timestamp': 1,
                    'sequence': 1,
                    'n_adv_raw': 1,
                    'devices': 1,
                    'gps_data': 1
                }
            ).sort('timestamp', 1))
            
            # Calculate unique devices and total advertisements
            unique_devices = set()
            total_advertisements = 0
            
            for record in data:
                if 'devices' in record:
                    for device in record['devices']:
                        if 'mac' in device:
                            unique_devices.add(device['mac'])
                        if 'n_adv' in device:
                            total_advertisements += device['n_adv']

            # Convert to GeoJSON
            features = []
            latest_gps = None
            
            for record in data:
                try:
                    gps_data = record.get('gps_data')
                    if not gps_data or not isinstance(gps_data, dict):
                        continue
                    
                    coords = gps_data.get('coordinates', {})
                    if not coords:
                        continue
                    
                    try:
                        longitude = float(coords.get('longitude', 0))
                        latitude = float(coords.get('latitude', 0))
                        
                        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
                            continue
                            
                        feature = {
                            "type": "Feature",
                            "geometry": {
                                "type": "Point",
                                "coordinates": [longitude, latitude]
                            },
                            "properties": {
                                "type": "gps",
                                "timestamp": record['timestamp'].isoformat(),
                                "speed": float(gps_data.get('speed', 0))
                            }
                        }
                        features.append(feature)
                        latest_gps = feature
                        
                    except (ValueError, TypeError) as e:
                        print(f"Error converting coordinates: {e}")
                        continue
                        
                except Exception as e:
                    print(f"Error processing record: {e}")
                    continue

            response_data = {
                "geojson": {
                    "type": "FeatureCollection",
                    "features": features
                },
                "stats": {
                    "total_buffers": collection.estimated_document_count(),
                    "recent_buffers": len(data),
                    "recent_buffers_label": f"Buffers ({time_range.upper()})",
                    "unique_devices": len(unique_devices),
                    "total_advertisements": total_advertisements,
                    "last_sequence": data[-1]['sequence'] if data else None,
                    "last_timestamp": data[-1]['timestamp'].isoformat() if data else None
                }
            }
            
            return jsonify(response_data)
            
        except Exception as e:
            print(f"MongoDB error: {e}")
            return jsonify({"error": "Database error"}), 500

    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Flask BLE GPS Tracker Server')
    parser.add_argument('--host', type=str, default='0.0.0.0')
    parser.add_argument('--port', type=int, default=5000)
    
    args = parser.parse_args()
    
    # Configurar Flask para producción
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 300  # Cache de 5 minutos
    app.config['TEMPLATES_AUTO_RELOAD'] = False
    
    print(f"\nServidor iniciado!")
    print(f"Para acceder desde dispositivos en la red local:")
    
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"1. Usando IP local: http://{local_ip}:{args.port}")
    print(f"2. Usando hostname: http://{hostname}:{args.port}")
    
    app.run(
        host=args.host,
        port=args.port,
        debug=False,  # Deshabilitar debug en producción
        threaded=True
    )
