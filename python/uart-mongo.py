import serial
from datetime import datetime
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
        self.collection = self.db.advertisements

    def _store_message(self, message):
        """Almacena el mensaje en MongoDB"""
        try:
            # Prepara el documento para MongoDB
            document = {
                'timestamp': datetime.now(),
                'sequence': message['sequence'],
                'mac': message['mac'],
                'addr_type': message['addr_type'],
                'adv_type': message['adv_type'],
                'rssi': message['rssi'],
                'data_len': message['data_len'],
                'data': message['data'].hex(),  # Convierte bytes a string hex
            }
            
            # Inserta en la base de datos
            result = self.collection.insert_one(document)
            print(f"Mensaje almacenado en la base de datos (ID: {result.inserted_id})")
            
            return True
        except Exception as e:
            print(f"Error almacenando en la base de datos: {e}")
            return False

    def receive_messages(self):
        """Método para recibir y almacenar"""
        print("Iniciando recepción de mensajes...")
        
        while True:
            try:
                # Busca la cabecera
                while True:
                    if self.serial.read() == b'\x55':
                        potential_header = b'\x55' + self.serial.read(3)
                        if potential_header == self.HEADER_MAGIC:
                            break

                # Lee el resto del mensaje
                remaining_data = self.serial.read(self.TOTAL_LENGTH - 4)
                full_message = potential_header + remaining_data

                # Parsea y procesa el mensaje
                message = self._parse_message(full_message)
                if message:
                    self._check_sequence(message['sequence'])
                    
                    # Almacena el mensage
                    self._store_message(message)
                    
                    # Imprime información del mensaje
                    print("\n=== Mensaje Recibido y Almacenado ===")
                    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                    print(f"Secuencia: {message['sequence']}")
                    print(f"MAC: {message['mac']}")
                    print(f"RSSI: {message['rssi']} dBm")
                    print("================================\n")

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
    try:
        receiver = UARTMongoReceiver(
            port='COM21',
            mongo_uri="mongodb://localhost:27017/"
        )
        receiver.receive_messages()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        receiver.close()