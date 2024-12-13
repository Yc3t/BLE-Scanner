import serial
import struct
from datetime import datetime

class UARTReceiver:
    def __init__(self, port='COM21', baudrate=115200):
        """Inicializa el receptor UART"""
        self.serial = serial.Serial(port, baudrate)
        self.sequence = 0  # Para detectar pérdida de mensajes
        
        # Formato del mensaje
        self.HEADER_MAGIC = b'\x55\x55\x55\x55'
        self.MESSAGE_FORMAT = {
            'header': 4,      # 4 bytes de cabecera
            'type': 1,       # 1 byte tipo mensaje
            'sequence': 1,    # 1 byte número secuencia
            'mac': 6,        # 6 bytes dirección MAC
            'addr_type': 1,  # 1 byte tipo dirección
            'adv_type': 1,   # 1 byte tipo advertisement
            'rssi': 1,       # 1 byte RSSI
            'data_len': 1,   # 1 byte longitud datos
            'data': 31,      # 31 bytes datos
        }
        self.TOTAL_LENGTH = sum(self.MESSAGE_FORMAT.values())
    def _check_header(self, data):
        """Verifica la cabecera del mensaje"""
        return data[:4] == self.HEADER_MAGIC

    def _parse_message(self, data):
        """Parsea el mensaje recibido"""
        try:
            offset = 0
            message = {}
            
            # Verifica cabecera
            if not self._check_header(data):
                return None
            offset += 4

            # Tipo de mensaje
            message['type'] = data[offset]
            offset += 1

            # Número de secuencia
            message['sequence'] = data[offset]
            offset += 1

            # Datos del advertisement
            message['mac'] = ':'.join(f'{b:02X}' for b in data[offset:offset+6])
            offset += 6

            message['addr_type'] = data[offset]
            offset += 1

            message['adv_type'] = data[offset]
            offset += 1

            # RSSI conversion from two's complement
            rssi_byte = data[offset]
            message['rssi'] = -(256 - rssi_byte) if rssi_byte > 127 else -rssi_byte
            offset += 1

            message['data_len'] = data[offset]
            offset += 1

            message['data'] = data[offset:offset+31]
            
            return message

        except Exception as e:
            print(f"Error parseando mensaje: {e}")
            return None

    def _check_sequence(self, received_seq):
        """Verifica la secuencia del mensaje"""
        if received_seq != (self.sequence + 1) % 256:
            print(f"¡Pérdida de mensaje! Esperado: {(self.sequence + 1) % 256}, Recibido: {received_seq}")
        self.sequence = received_seq

    def receive_messages(self):
        """Recibe y procesa mensajes continuamente"""
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
                    
                    # Imprime información del mensaje
                    print("\n=== Mensaje Recibido ===")
                    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                    print(f"Secuencia: {message['sequence']}")
                    print(f"MAC: {message['mac']}")
                    print(f"Tipo Addr: {message['addr_type']}")
                    print(f"Tipo Adv: {message['adv_type']}")
                    print(f"RSSI: {message['rssi']} dBm")
                    print(f"Longitud datos: {message['data_len']}")
                    print("====================\n")

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
        """Cierra la conexión serial"""
        if self.serial.is_open:
            self.serial.close()

if __name__ == "__main__":
    try:
        receiver = UARTReceiver(port='COM21')  
        receiver.receive_messages()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        receiver.close()