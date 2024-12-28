import serial
from datetime import datetime
import time
import argparse
from pymongo import MongoClient
from uart import UARTReceiver
from icecream import ic
import logging
import os

class UARTMongoReceiver(UARTReceiver):
    def __init__(self, port='COM20', baudrate=115200, 
                 mongo_uri="mongodb://localhost:27017/"):
        """Inicializa el receptor UART con MongoDB"""
        # Configurar logging primero
        self._setup_logging()
        self.logger.info("Iniciando receptor UART con MongoDB")
        
        super().__init__(port, baudrate)
        
        # Conexión a MongoDB
        try:
            self.client = MongoClient(mongo_uri)
            self.db = self.client.ble_scanner
            self.collection = self.db.test3
            self.logger.info("Conexión a MongoDB establecida")
        except Exception as e:
            self.logger.error(f"Error conectando a MongoDB: {e}")
            raise

    def _setup_logging(self):
        """Configura el sistema de logging"""
        # Crear directorio de logs si no existe
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Nombre del archivo de log con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"uart_mongo_{timestamp}.log")
        
        # Configurar logging
        self.logger = logging.getLogger('UART_Mongo_Receiver')
        self.logger.setLevel(logging.DEBUG)
        
        # Handler para archivo
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formato del log
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Agregar handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

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
            self.logger.debug(f"Buffer almacenado en BD - ID: {result.inserted_id}")
            self.logger.debug(f"Datos del buffer - Secuencia: {header['sequence']}, MACs: {len(devices)}")
            return True
        except Exception as e:
            self.logger.error(f"Error almacenando en BD: {e}")
            return False

    def receive_messages(self, duration=None):
        """Recibe y almacena buffers durante un tiempo específico"""
        self.logger.info("Iniciando recepción de buffers...")
        start_time = time.time()
        buffers_procesados = 0
        
        while True:
            try:
                # Verificar tiempo transcurrido
                if duration and (time.time() - start_time) >= duration:
                    self.logger.info(f"Tiempo de ejecución ({duration}s) completado")
                    self.logger.info(f"Total de buffers procesados: {buffers_procesados}")
                    break

                # Busca la cabecera
                while True:
                    if self.serial.read() == b'\x55':
                        potential_header = b'\x55' + self.serial.read(3)
                        if potential_header == self.HEADER_MAGIC:
                            self.logger.debug("Cabecera UART encontrada")
                            break

                # Lee y parsea la cabecera
                header_data = potential_header + self.serial.read(self.HEADER_LENGTH - 4)
                header = self._parse_header(header_data)
                
                if not header:
                    self.logger.warning("Error al parsear cabecera")
                    continue

                # Lee todos los dispositivos
                devices = []
                for i in range(header['n_mac']):
                    device_data = self.serial.read(self.DEVICE_LENGTH)
                    device = self._parse_device(device_data)
                    if device:
                        devices.append(device)
                        self.logger.debug(f"Dispositivo {i+1} parseado - MAC: {device['mac']}")

                # Almacena el buffer completo
                if devices:
                    if self._store_buffer(header, devices):
                        buffers_procesados += 1
                        self.logger.info(
                            f"Buffer #{buffers_procesados} procesado - "
                            f"Secuencia: {header['sequence']}, "
                            f"Dispositivos: {len(devices)}, "
                            f"N_ADV_RAW: {header['n_adv_raw']}"
                        )

            except serial.SerialException as e:
                self.logger.error(f"Error de comunicación serial: {e}")
                break
            except KeyboardInterrupt:
                self.logger.info(f"Recepción interrumpida por el usuario")
                self.logger.info(f"Total de buffers procesados: {buffers_procesados}")
                break
            except Exception as e:
                self.logger.error(f"Error inesperado: {e}")
                continue

    def close(self):
        """Cierra las conexiones"""
        try:
            super().close()  # Cierra el puerto serial
            self.logger.info("Puerto serial cerrado")
            self.client.close()  # Cierra la conexión MongoDB
            self.logger.info("Conexión MongoDB cerrada")
        except Exception as e:
            self.logger.error(f"Error al cerrar conexiones: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Receptor BLE Scanner UART MongoDB')
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
        receiver.logger.info("Iniciando captura %s", 
                           "indefinida" if not args.duration else f"por {args.duration} segundos")
        receiver.receive_messages(duration=args.duration)
    except Exception as e:
        if hasattr(receiver, 'logger'):
            receiver.logger.error(f"Error: {e}")
        else:
            print(f"Error: {e}")
    finally:
        if hasattr(receiver, 'close'):
            receiver.close()