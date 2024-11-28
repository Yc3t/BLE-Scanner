#!/usr/bin/env python3
import serial
import struct
import time
from datetime import datetime
import sys

class BLEScanner:
    # Constantes del protocolo
    HEADER_PATTERN = b'\x55\x55\x55\x55'  # Patrón de sincronización
    MSG_TYPE_ADV = 0x01                   # Tipo mensaje: datos advertisement
    
    def __init__(self, port="/dev/ttyUSB0", baudrate=115200):
        """Inicializa el scanner BLE."""
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.last_sequence = None
        self.messages_received = 0
        self.messages_lost = 0
        
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
                
    def process_message(self, data):
        """Procesa un mensaje completo."""
        try:
            # Extrae campos del mensaje
            msg_type = data[0]
            sequence = data[1]
            
            # Verifica tipo de mensaje
            if msg_type != self.MSG_TYPE_ADV:
                print(f"Tipo de mensaje desconocido: {msg_type}")
                return
            
            # Control de secuencia
            if self.last_sequence is not None:
                expected = (self.last_sequence + 1) & 0xFF
                if sequence != expected:
                    lost = (sequence - expected) & 0xFF
                    self.messages_lost += lost
                    print(f"\n¡Pérdida de {lost} mensajes detectada!")
            self.last_sequence = sequence
            
            # Extrae datos del advertisement
            addr = ':'.join(f'{x:02X}' for x in data[2:8][::-1])  # MAC en formato invertido
            addr_type = "Aleatoria" if data[8] else "Pública"
            adv_type = data[9]
            rssi = struct.unpack('b', bytes([data[10]]))[0]  # RSSI como signed char
            data_len = data[11]
            adv_data = data[12:12+data_len]
            
            # Imprime información
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            print(f"\n=== Mensaje #{self.messages_received} (Seq: {sequence}) - {timestamp} ===")
            print(f"MAC: {addr} ({addr_type})")
            print(f"Tipo: 0x{adv_type:02X}, RSSI: {rssi} dBm")
            print("Datos:", ' '.join(f'{x:02X}' for x in adv_data))
            
            # Actualiza estadísticas
            self.messages_received += 1
            
            # Muestra estadísticas periódicamente
            if self.messages_received % 100 == 0:
                self.print_stats()
                
        except Exception as e:
            print(f"\nError procesando mensaje: {e}")
            
    def print_stats(self):
        """Muestra estadísticas de recepción."""
        total_expected = self.messages_received + self.messages_lost
        loss_rate = (self.messages_lost / total_expected * 100) if total_expected > 0 else 0
        
        print("\n=== Estadísticas ===")
        print(f"Mensajes recibidos: {self.messages_received}")
        print(f"Mensajes perdidos: {self.messages_lost}")
        print(f"Tasa de pérdida: {loss_rate:.2f}%")
        
    def run(self):
        """Bucle principal de recepción."""
        if not self.connect():
            return
        
        print("Esperando mensajes... (Ctrl+C para salir)")
        
        try:
            while True:
                # Busca patrón de sincronización
                if not self.find_header():
                    continue
                
                # Lee el resto del mensaje
                message_data = self.serial.read(2)  # tipo + secuencia
                if len(message_data) != 2:
                    print("Error: Timeout leyendo cabecera")
                    continue
                
                # Lee datos de advertisement (tamaño fijo)
                adv_data = self.serial.read(31 + 12)  # 31 bytes payload + 12 bytes header
                if len(adv_data) != 43:
                    print("Error: Timeout leyendo datos")
                    continue
                
                # Procesa mensaje completo
                self.process_message(message_data + adv_data)
                
        except KeyboardInterrupt:
            print("\nPrograma terminado por usuario")
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            if self.serial:
                self.serial.close()
            self.print_stats()

if __name__ == "__main__":
    # Permite especificar puerto serie como argumento
    port = sys.argv[1] if len(sys.argv) > 1 else "COM9"
    
    scanner = BLEScanner(port=port)
    scanner.run()