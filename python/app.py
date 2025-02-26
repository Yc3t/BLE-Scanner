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
collection = db.portfinal

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
        wifi_info = {
            "wifi_name": "Unknown",
            "signal_strength": None
        }
        
        try:
            # Get wireless interface info with error handling
            netsh_output = subprocess.check_output(
                ['netsh', 'wlan', 'show', 'interfaces'], 
                stderr=subprocess.STDOUT, 
                text=True,
                timeout=5  # Add timeout
            )
            
            for line in netsh_output.split('\n'):
                if 'SSID' in line and 'BSSID' not in line:
                    wifi_info["wifi_name"] = line.split(':')[1].strip()
                if 'Signal' in line:
                    try:
                        signal_str = line.split(':')[1].strip().replace('%', '')
                        wifi_info["signal_strength"] = int(signal_str)
                    except:
                        pass

        except subprocess.TimeoutExpired:
            print("Warning: WiFi info command timed out")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not get WiFi info - {str(e)}")
        except Exception as e:
            print(f"Warning: Unexpected error getting WiFi info - {str(e)}")

        return {
            "wifi_name": wifi_info["wifi_name"],
            "signal_strength": wifi_info["signal_strength"],
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
        
        # Get all records from MongoDB with sorting
        print("Fetching all available records from database...")
        data = list(collection.find(
            {},  # Empty query to get all records
            {"_id": 0}
        ).sort("timestamp", -1))  # Sort by timestamp in descending order
        
        print(f"Found {len(data)} total records in database")

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
                                if d.get('sequence') is not None:  # Only add if it's a buffer entry
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
        # Get total count of documents in collection
        total_buffers = collection.count_documents({})

        for d in data:
            if 'devices' in d and isinstance(d['devices'], list):
                for device in d['devices']:
                    if isinstance(device, dict):
                        if 'mac' in device:
                            unique_macs.add(device['mac'])
                        if 'n_adv' in device:
                            total_advertisements += device['n_adv']

        last_timestamp = max([d["timestamp"] for d in data]) if data else datetime.utcnow()
        
        # Get the latest sequence number correctly
        latest_doc = collection.find_one(
            {"sequence": {"$exists": True}},
            sort=[("timestamp", -1)]
        )
        last_sequence = latest_doc.get('sequence', 0) if latest_doc else 0

        # Calculate chart data
        chart_data = calculate_devices_per_buffer(data)
        
        # Get system info
        system_info = get_system_info()
        
        # Get last record safely
        last_record = data[-1] if data else None
        last_gps = last_record.get('gps_data', {}) if last_record else {}
        last_coordinates = last_gps.get('coordinates', {}) if isinstance(last_gps, dict) else {}
        
        # Format response
        response = {
            "geojson": {
                "type": "FeatureCollection",
                "features": gps_points + buffer_points
            },
            "stats": {
                "total_buffers": total_buffers,
                "recent_buffers": len(buffer_points),
                "recent_buffers_label": f"Buffers ({time_range})",
                "unique_devices": len(unique_macs),
                "total_advertisements": total_advertisements,
                "last_sequence": last_sequence,
                "last_timestamp": last_timestamp.isoformat(),
                "last_speed": float(last_gps.get('speed', 0) if isinstance(last_gps, dict) else 0),
                "last_latitude": float(last_coordinates.get('latitude', 0) if isinstance(last_coordinates, dict) else 0),
                "last_longitude": float(last_coordinates.get('longitude', 0) if isinstance(last_coordinates, dict) else 0),
                "last_n_mac": int(last_record.get('n_mac', 0) if last_record else 0)
            },
            "chartData": chart_data,
            "systemInfo": system_info
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
    def get_ip_addresses():
        ip_list = []
        try:
            # Get all network interfaces
            interfaces = socket.getaddrinfo(host=socket.gethostname(), port=None, family=socket.AF_INET)
            for interface in interfaces:
                ip = interface[4][0]
                if not ip.startswith('127.'):  # Filter out localhost
                    ip_list.append(ip)
            return list(set(ip_list))  # Remove duplicates
        except Exception as e:
            print(f"Error getting IP addresses: {e}")
            return []

    # Get and print all available IP addresses
    ip_addresses = get_ip_addresses()
    print("\nAvailable IP addresses:")
    for ip in ip_addresses:
        print(f"Backend: http://{ip}:{args.port}")
        print(f"Frontend: http://{ip}:5173")
    
    print("\nOr use hostname:")
    hostname = socket.gethostname()
    print(f"Backend: http://{hostname}:{args.port}")
    print(f"Frontend: http://{hostname}:5173")
    
    app.run(
        host=args.host,
        port=args.port,
        debug=True,
        threaded=True
    )
