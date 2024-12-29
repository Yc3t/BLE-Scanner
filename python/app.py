from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient
from datetime import datetime, timedelta
from flask_compress import Compress
from flask_cors import CORS
from collections import defaultdict
import psutil  # For battery info
import subprocess  # For WiFi info

app = Flask(__name__)
Compress(app)
CORS(app)

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client.tracking_data
collection = db.port2

def calculate_devices_per_buffer(data, max_points=13):
    """Calculate devices per buffer for the chart"""
    if not data:
        return []
    
    # Sort data by timestamp
    sorted_data = sorted(data, key=lambda x: x['timestamp'])
    
    # Calculate devices per buffer
    buffer_stats = []
    for doc in sorted_data:
        if 'devices' in doc:
            buffer_stats.append({
                'buffer': doc['sequence'],
                'devices': len(doc['devices']),
                'timestamp': doc['timestamp']
            })
    
    # If we have more points than max_points, aggregate them
    if len(buffer_stats) > max_points:
        # Calculate step size
        step = len(buffer_stats) // max_points
        
        # Aggregate points
        aggregated_stats = []
        for i in range(0, len(buffer_stats), step):
            chunk = buffer_stats[i:i + step]
            avg_devices = sum(stat['devices'] for stat in chunk) / len(chunk)
            aggregated_stats.append({
                'buffer': chunk[-1]['buffer'],
                'devices': round(avg_devices, 1),
                'timestamp': chunk[-1]['timestamp']
            })
        
        buffer_stats = aggregated_stats[:max_points]
    
    return buffer_stats

def get_system_info():
    """Get WiFi and battery information for Windows"""
    try:
        # Get battery info using psutil
        battery = psutil.sensors_battery()
        battery_percent = int(battery.percent) if battery else None
        power_plugged = battery.power_plugged if battery else None

        # Get WiFi info using netsh command (Windows specific)
        try:
            # Get wireless interface info
            netsh_output = subprocess.check_output(
                ['netsh', 'wlan', 'show', 'interfaces'], 
                stderr=subprocess.STDOUT, 
                text=True
            )
            
            essid = None
            signal_strength = None
            
            for line in netsh_output.split('\n'):
                if 'SSID' in line and 'BSSID' not in line:
                    essid = line.split(':')[1].strip()
                if 'Signal' in line:
                    try:
                        # Windows provides signal strength as percentage
                        signal_str = line.split(':')[1].strip().replace('%', '')
                        signal_strength = int(signal_str)
                    except:
                        signal_strength = None

        except Exception as e:
            print(f"Error getting WiFi info: {e}")
            essid = "Unknown"
            signal_strength = None

        return {
            "wifi_name": essid or "Not Connected",
            "signal_strength": signal_strength,
            "battery_level": battery_percent,
            "power_plugged": power_plugged
        }
    except Exception as e:
        print(f"Error getting system info: {e}")
        return {
            "wifi_name": "Unknown",
            "signal_strength": None,
            "battery_level": None,
            "power_plugged": None
        }

@app.route('/api/data')
def get_data():
    try:
        time_range = request.args.get('timeRange', '5m')
        print(f"\nReceived request for timeRange: {time_range}")
        
        # Parse time range
        value = int(time_range[:-1])
        unit = time_range[-1]
        
        if unit == 'h':
            delta = timedelta(hours=value)
        elif unit == 'd':
            delta = timedelta(days=value)
        else:  # 'm' for minutes
            delta = timedelta(minutes=value)
        
        since = datetime.utcnow() - delta
        print(f"Fetching data since: {since}")
        
        # Get data from MongoDB with sorting
        data = list(collection.find(
            {"timestamp": {"$gte": since}},
            {"_id": 0}
        ).sort("timestamp", 1))
        
        print(f"Found {len(data)} records")

        # Process GPS points and buffer locations
        gps_points = []
        buffer_points = []
        
        for d in data:
            # Process GPS data for trail
            if 'gps_data' in d and isinstance(d['gps_data'], dict):
                gps_data = d['gps_data']
                if 'coordinates' in gps_data:
                    coords = gps_data['coordinates']
                    if isinstance(coords, dict) and 'latitude' in coords and 'longitude' in coords:
                        try:
                            latitude = float(coords['latitude'])
                            longitude = float(coords['longitude'])
                            if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                                # Add GPS point for trail
                                gps_points.append({
                                    "type": "Feature",
                                    "geometry": {
                                        "type": "Point",
                                        "coordinates": [longitude, latitude]
                                    },
                                    "properties": {
                                        "type": "gps",
                                        "timestamp": d['timestamp'].isoformat(),
                                        "speed": float(gps_data.get('speed', 0))
                                    }
                                })
                                
                                # Add buffer point with BLE data
                                devices = d.get('devices', [])
                                buffer_points.append({
                                    "type": "Feature",
                                    "geometry": {
                                        "type": "Point",
                                        "coordinates": [longitude, latitude]
                                    },
                                    "properties": {
                                        "type": "buffer",
                                        "timestamp": d['timestamp'].isoformat(),
                                        "sequence": d.get('sequence', 0),
                                        "n_devices": len(devices),
                                        "n_adv_raw": d.get('n_adv_raw', 0),
                                        "devices": [
                                            {
                                                "mac": dev.get('mac', 'unknown'),
                                                "rssi": dev.get('rssi', 0),
                                                "n_adv": dev.get('n_adv', 0)
                                            }
                                            for dev in devices
                                        ]
                                    }
                                })
                        except (ValueError, TypeError):
                            continue

        print(f"GPS points: {len(gps_points)}")
        print(f"Buffer points: {len(buffer_points)}")

        # Calculate BLE stats
        unique_macs = set()
        total_advertisements = 0
        last_sequence = 0

        for d in data:
            if 'devices' in d and isinstance(d['devices'], list):
                for device in d['devices']:
                    if isinstance(device, dict):
                        if 'mac' in device:
                            unique_macs.add(device['mac'])
                        if 'n_adv' in device:
                            total_advertisements += device['n_adv']
            if 'sequence' in d:
                last_sequence = max(last_sequence, d['sequence'])

        last_timestamp = max([d["timestamp"] for d in data]) if data else datetime.utcnow()
        
        # Calculate chart data
        chart_data = calculate_devices_per_buffer(data)
        
        # Get system info
        system_info = get_system_info()
        
        # Format response
        response = {
            "geojson": {
                "type": "FeatureCollection",
                "features": gps_points + buffer_points  # Combine both types of points
            },
            "stats": {
                "total_buffers": len(data),
                "recent_buffers": len(buffer_points),
                "recent_buffers_label": f"Buffers ({time_range})",
                "unique_devices": len(unique_macs),
                "total_advertisements": total_advertisements,
                "last_sequence": last_sequence,
                "last_timestamp": last_timestamp.isoformat()
            },
            "chartData": chart_data,
            "systemInfo": system_info  # Add system info to response
        }
        
        print("Response prepared successfully")
        return jsonify(response)
    except Exception as e:
        print(f"Error in get_data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "geojson": {"type": "FeatureCollection", "features": []},
            "stats": {
                "total_buffers": 0,
                "recent_buffers": 0,
                "recent_buffers_label": f"Buffers ({time_range})",
                "unique_devices": 0,
                "total_advertisements": 0,
                "last_sequence": 0,
                "last_timestamp": datetime.utcnow().isoformat()
            },
            "chartData": [],
            "systemInfo": {
                "wifi_name": "Error",
                "signal_strength": None,
                "battery_level": None,
                "power_plugged": None
            }
        }), 500

if __name__ == '__main__':
    # Test MongoDB connection
    try:
        print("\nTesting MongoDB connection...")
        count = collection.count_documents({})
        print(f"Connected successfully. Found {count} documents in collection")
        
        # Print a sample document
        sample = collection.find_one()
        if sample:
            print("\nSample document structure:")
            for key, value in sample.items():
                print(f"{key}: {type(value)}")
    except Exception as e:
        print(f"MongoDB connection error: {e}")
    
    import argparse
    parser = argparse.ArgumentParser(description='Flask BLE GPS Tracker Server')
    parser.add_argument('--host', type=str, default='0.0.0.0')
    parser.add_argument('--port', type=int, default=5000)
    
    args = parser.parse_args()
    
    print(f"\nServer started!")
    print(f"Access from local network devices:")
    
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"1. Using local IP: http://{local_ip}:{args.port}")
    print(f"2. Using hostname: http://{hostname}:{args.port}")
    
    app.run(
        host=args.host,
        port=args.port,
        debug=True,
        threaded=True
    )
