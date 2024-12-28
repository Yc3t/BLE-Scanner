import serial
import time
import json
from datetime import datetime
import pynmea2
import os

class GPS_Tracker:
    def __init__(self, port='COM26', baud_rate=9600):
        self.port = port
        self.baud_rate = baud_rate
        self.coordinates = []
        self.timestamps = []
        
    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=1)
            print(f"Conectado al módulo GPS en {self.port}")
            time.sleep(2)  # Permitir que el módulo GPS se estabilice
        except serial.SerialException as e:
            print(f"Error al conectar al GPS: {e}")
            raise
            
    def read_gps_data(self, duration=60):
        if not hasattr(self, 'ser'):
            print("GPS no conectado. Por favor, llame a connect() primero.")
            return
            
        start_time = time.time()
        print("Esperando señal GPS...")
        
        while (time.time() - start_time) < duration:
            try:
                line = self.ser.readline().decode('ascii', errors='replace')
                
                # Analizar las sentencias GPRMC y GPGGA
                if line.startswith('$GPRMC'):
                    msg = pynmea2.parse(line)
                    print(f"\nEstado GPRMC: {'Válido' if msg.status == 'A' else 'Inválido'}")
                    if msg.status == 'A':  # 'A' significa posición válida
                        self.coordinates.append((msg.longitude, msg.latitude))
                        self.timestamps.append(msg.datetime.isoformat() if msg.datetime else datetime.now().isoformat())
                        print(f"Posición: Lon: {msg.longitude}, Lat: {msg.latitude}")
                        print(f"Velocidad: {msg.spd_over_grnd} nudos")
                        try:
                            self.save_geojson()
                        except Exception as e:
                            print(f"Error al guardar datos: {e}")
                
                elif line.startswith('$GPGGA'):
                    msg = pynmea2.parse(line)
                    print(f"\nCalidad GPGGA: {msg.gps_qual} (0=Inválido, 1=GPS fijo, 2=DGPS fijo)")
                    print(f"Satélites en uso: {msg.num_sats}")
                    print(f"HDOP: {msg.horizontal_dil}")
                    if msg.gps_qual > 0:  # Tenemos señal
                        print(f"Posición: Lon: {msg.longitude}, Lat: {msg.latitude}")
                        print(f"Altitud: {msg.altitude} {msg.altitude_units}")

            except Exception as e:
                print(f"Error al leer datos GPS: {e}")
                
    def save_geojson(self, filename='gps_track.geojson'):
        """Guardar datos GPS como GeoJSON con marcas de tiempo y metadatos"""
        if not self.coordinates:
            print("No hay coordenadas GPS para guardar")
            return
            
        # Imprimir información de depuración
        print(f"Guardando {len(self.coordinates)} coordenadas en {filename}")
        
        # Crear ruta completa para el archivo
        full_path = os.path.abspath(filename)
        
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": self.coordinates
                    },
                    "properties": {
                        "name": "GPS Track",
                        "timestamps": self.timestamps,
                        "start_time": self.timestamps[0] if self.timestamps else None,
                        "end_time": self.timestamps[-1] if self.timestamps else None,
                        "points": len(self.coordinates)
                    }
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": self.coordinates[0]
                    },
                    "properties": {
                        "name": "Punto Inicial",
                        "time": self.timestamps[0] if self.timestamps else None,
                        "marker-color": "#00ff00"
                    }
                }
            ]
        }
        
        # Agregar punto final solo si tenemos más de una coordenada
        if len(self.coordinates) > 1:
            geojson["features"].append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": self.coordinates[-1]
                },
                "properties": {
                    "name": "Punto Final",
                    "time": self.timestamps[-1] if self.timestamps else None,
                    "marker-color": "#ff0000"
                }
            })
            
        try:
            with open(full_path, 'w') as f:
                json.dump(geojson, f, indent=2)
            print(f"GeoJSON guardado como {full_path}")
        except Exception as e:
            print(f"Error al escribir en el archivo: {e}")
        
    def close(self):
        if hasattr(self, 'ser'):
            self.ser.close()

def list_com_ports():
    """Listar todos los puertos COM disponibles"""
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("¡No se encontraron puertos COM!")
        return
    print("\nPuertos COM disponibles:")
    for port in ports:
        print(f"- {port.device}: {port.description}")

if __name__ == "__main__":
    # Listar puertos disponibles
    list_com_ports()
    
    # Pedir al usuario que seleccione un puerto
    port = input("\nIngrese el puerto COM (ej., COM26): ").strip()
    
    # Crear instancia del rastreador GPS
    tracker = GPS_Tracker(port=port)
    
    try:
        # Conectar al GPS
        tracker.connect()
        
        # Leer datos GPS durante 5 minutos
        print("Leyendo datos GPS durante 5 minutos...")
        tracker.read_gps_data(duration=300)
        
    except KeyboardInterrupt:
        print("\nSeguimiento detenido por el usuario")
    except Exception as e:
        print(f"Ocurrió un error: {e}")
    finally:
        tracker.close()
        print("Conexión GPS cerrada")