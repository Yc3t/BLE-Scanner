import serial
from datetime import datetime
import time
import argparse
from pymongo import MongoClient
from uart import UARTReceiver

class UARTMongoReceiver(UARTReceiver):
    def __init__(self, port='COM20', baudrate=115200, 
                 mongo_uri="mongodb://localhost:27017/"):
        """Inicializa el receptor UART con MongoDB"""
        super().__init__(port, baudrate)
        
        # Conexión a MongoDB
        self.client = MongoClient(mongo_uri)
        self.db = self.client.ble_scanner
        self.collection = self.db.adv_buffer1

    def _store_buffer(self, header, devices):
        """Almacena el buffer completo en MongoDB"""
        try:
            document = {
                'timestamp': datetime.now(),
                'sequence': header['sequence'],
                'n_adv_raw': header['n_adv_raw'],
                'n_mac': header['n_mac'],
                'devices': []
            }

            for device in devices:
                device_doc = {
                    'mac': device['mac'],
                    'addr_type': device['addr_type'],
                    'adv_type': device['adv_type'],
                    'rssi': device['rssi'],
                    'data_len': device['data_len'],
                    'data': device['data'].hex(),
                    'n_adv': device['n_adv']
                }
                document['devices'].append(device_doc)
            
            result = self.collection.insert_one(document)
            print(f"Buffer almacenado en la base de datos (ID: {result.inserted_id})")
            return True
        except Exception as e:
            print(f"Error almacenando en la base de datos: {e}")
            return False

    def receive_messages(self, duration=None):
        """Recibe y almacena buffers durante un tiempo específico
        
        Args:
            duration (int, optional): Duración en segundos. None para ejecución indefinida.
        """
        print("Iniciando recepción de buffers...")
        start_time = time.time()
        
        while True:
            try:
                # Verificar tiempo transcurrido
                if duration and (time.time() - start_time) >= duration:
                    print(f"\nTiempo de ejecución ({duration}s) completado")
                    break

                # Busca la cabecera
                while True:
                    if self.serial.read() == b'\x55':
                        potential_header = b'\x55' + self.serial.read(3)
                        if potential_header == self.HEADER_MAGIC:
                            break

                # Lee y parsea la cabecera
                header_data = potential_header + self.serial.read(self.HEADER_LENGTH - 4)
                header = self._parse_header(header_data)
                
                if not header:
                    continue

                # Lee todos los dispositivos
                devices = []
                for _ in range(header['n_mac']):
                    device_data = self.serial.read(self.DEVICE_LENGTH)
                    device = self._parse_device(device_data)
                    if device:
                        devices.append(device)

                # Almacena el buffer completo
                if devices:
                    self._store_buffer(header, devices)
                    
                    print("\n=== Buffer Almacenado ===")
                    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                    print(f"Secuencia: {header['sequence']}")
                    print(f"Dispositivos: {len(devices)}")
                    print("=====================\n")

            except serial.SerialException as e:
                print(f"Error de comunicación serial: {e}")
                break
            except KeyboardInterrupt:
                print("\nRecepción interrumpida por el usuario")
                break
            except Exception as e:
                print(f"Error inesperado: {e}")
                continue

    def close(self):
        """Cierra las conexiones"""
        super().close()  # Cierra el puerto serial
        self.client.close()  # Cierra la conexión MongoDB

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='BLE Scanner UART MongoDB Receiver')
    parser.add_argument('--port', type=str, default='COM20',
                      help='Puerto serial (default: COM20)')
    parser.add_argument('--duration', type=int,
                      help='Duración de la captura en segundos')
    parser.add_argument('--mongo-uri', type=str, 
                      default="mongodb://localhost:27017/",
                      help='URI de MongoDB (default: mongodb://localhost:27017/)')
    
    args = parser.parse_args()
    
    try:
        receiver = UARTMongoReceiver(
            port=args.port,
            mongo_uri=args.mongo_uri
        )
        print(f"Iniciando captura{'.' if not args.duration else f' por {args.duration} segundos.'}")
        receiver.receive_messages(duration=args.duration)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        receiver.close()