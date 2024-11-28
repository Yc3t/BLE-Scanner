#!/usr/bin/env python3
import serial
import struct
import time
from datetime import datetime
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionError, WriteError

class BLEMongoScanner:
    # Constantes del protocolo
    HEADER_PATTERN = b'\x55\x55\x55\x55'
    MSG_TYPE_ADV = 0x01
    
    def __init__(self, port="/dev/ttyUSB0", baudrate=115200, 
                 mongo_uri="mongodb://localhost:27017/"):
        """Inicializa el scanner BLE con conexión a MongoDB."""
        # Configuración Serial
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        
        # Contadores y control
        self.last_sequence = None
        self.messages_received = 0
        self.messages_lost = 0
        
        # Configuración MongoDB
        try:
            self.client = MongoClient(mongo_uri)
            self.db = self.client.ble_scanner
            self.collection = self.db.advertisements
            print("Conectado a MongoDB")
            
            # Crear índices para optimizar consultas
            self.collection.create_index([("timestamp", 1)])
            self.collection.create_index([("mac_address", 1)])
            
        except ConnectionError as e:
            print(f"Error conectando a MongoDB: {e}")
            sys.exit(1)

    def store_advertisement(self, advertisement_data):
        """Almacena el advertisement en MongoDB."""
        try:
            result = self.collection.insert_one(advertisement_data)
            return result.inserted_id
        except WriteError as e:
            print(f"Error escribiendo en MongoDB: {e}")
            return None

    def process_message(self, data):
        """Procesa y almacena un mensaje completo."""
        try:
            # Extrae campos del mensaje
            msg_type = data[0]
            sequence = data[1]
            
            # Control de secuencia
            if self.last_sequence is not None:
                expected = (self.last_sequence + 1) & 0xFF
                if sequence != expected:
                    lost = (sequence - expected) & 0xFF
                    self.messages_lost += lost
                    print(f"\n¡Pérdida de {lost} mensajes detectada!")
            self.last_sequence = sequence
            
            # Prepara documento para MongoDB
            timestamp = datetime.now()
            advertisement = {
                "timestamp": timestamp,
                "sequence": sequence,
                "mac_address": ':'.join(f'{x:02X}' for x in data[2:8][::-1]),
                "address_type": "Random" if data[8] else "Public",
                "adv_type": data[9],
                "rssi": struct.unpack('b', bytes([data[10]]))[0],
                "data_length": data[11],
                "raw_data": data[12:12+data[11]].hex(),
                "metadata": {
                    "received_at": timestamp.isoformat(),
                    "scanner_id": "scanner_001"  # Identificador único del scanner
                }
            }
            
            # Almacena en MongoDB
            doc_id = self.store_advertisement(advertisement)
            
            # Muestra información resumida
            print(f"\n[{timestamp.strftime('%H:%M:%S.%f')[:-3]}] "
                  f"MAC: {advertisement['mac_address']} "
                  f"RSSI: {advertisement['rssi']} dBm "
                  f"Seq: {sequence}")
            
            # Actualiza contadores
            self.messages_received += 1
            
            # Estadísticas periódicas
            if self.messages_received % 100 == 0:
                self.print_stats()
                
        except Exception as e:
            print(f"\nError procesando mensaje: {e}")
    
    def get_statistics(self):
        """Obtiene estadísticas de la base de datos."""
        try:
            total_docs = self.collection.count_documents({})
            
            # Encuentra el primer y último timestamp
            first = self.collection.find_one({}, sort=[("timestamp", 1)])
            last = self.collection.find_one({}, sort=[("timestamp", -1)])
            
            if first and last:
                time_span = last['timestamp'] - first['timestamp']
                
                stats = {
                    "total_advertisements": total_docs,
                    "time_span_seconds": time_span.total_seconds(),
                    "advertisements_per_second": total_docs / time_span.total_seconds(),
                    "first_advertisement": first['timestamp'],
                    "last_advertisement": last['timestamp']
                }
                
                return stats
            
        except Exception as e:
            print(f"Error obteniendo estadísticas: {e}")
            return None

    def print_stats(self):
        """Muestra estadísticas de recepción y base de datos."""
        print("\n=== Estadísticas ===")
        print(f"Mensajes recibidos: {self.messages_received}")
        print(f"Mensajes perdidos: {self.messages_lost}")
        
        # Estadísticas de MongoDB
        stats = self.get_statistics()
        if stats:
            print("\nEstadísticas MongoDB:")
            print(f"Total advertisements: {stats['total_advertisements']}")
            print(f"Tiempo total: {stats['time_span_seconds']:.2f} segundos")
            print(f"Advertisements/segundo: {stats['advertisements_per_second']:.2f}")

    def run(self):
        """Bucle principal de recepción y almacenamiento."""
        if not self.connect():
            return
        
        print("Escaneando y almacenando... (Ctrl+C para salir)")
        
        try:
            while True:
                if not self.find_header():
                    continue
                
                message_data = self.serial.read(2)
                if len(message_data) != 2:
                    continue
                
                adv_data = self.serial.read(43)
                if len(adv_data) != 43:
                    continue
                
                self.process_message(message_data + adv_data)
                
        except KeyboardInterrupt:
            print("\nPrograma terminado por usuario")
        finally:
            if self.serial:
                self.serial.close()
            self.print_stats()
            self.client.close()

    def connect(self):
        """Establece conexión con el puerto serie."""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            print(f"Conectado a {self.port} a {self.baudrate} baudios")
            return True
        except serial.SerialException as e:
            print(f"Error al abrir puerto serie: {e}")
            return False

    def find_header(self):
        """Busca el patrón de sincronización en el stream."""
        buffer = b''
        while True:
            if len(buffer) > 4:
                buffer = buffer[1:]
            byte = self.serial.read(1)
            if not byte:
                return False
            buffer += byte
            if buffer.endswith(self.HEADER_PATTERN):
                return True

if __name__ == "__main__":
    # Configuración por línea de comandos
    import argparse
    
    parser = argparse.ArgumentParser(description='BLE Scanner con almacenamiento MongoDB')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Puerto serie')
    parser.add_argument('--mongo', default='mongodb://localhost:27017/', 
                       help='URI de MongoDB')
    
    args = parser.parse_args()
    
    scanner = BLEMongoScanner(port=args.port, mongo_uri=args.mongo)
    scanner.run()