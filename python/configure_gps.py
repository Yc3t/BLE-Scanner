import serial
import time

def configure_gps(port="COM26", baudrate=9600):
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"Conectado al GPS en {port} con {baudrate} baudios")
        
        # Mensaje UBX para configurar baudrate a 115200
        ubx_set_baud = bytes([
            0xB5, 0x62,             # UBX header
            0x06, 0x00,             # CFG-PRT
            0x14, 0x00,             # Length (20 bytes)
            0x01,                   # Port ID (1 = UART1)
            0x00,                   # Reserved
            0x00, 0x00,            # TX Ready
            0xD0, 0x08, 0x00, 0x00, # Mode (8N1)
            0x00, 0xC2, 0x01, 0x00, # Baud rate (115200)
            0x07, 0x00,             # Input protocols
            0x03, 0x00,             # Output protocols
            0x00, 0x00,             # Flags
            0x00, 0x00,             # Reserved
            0xBC, 0x6A              # Checksum
        ])

        print("\nEnviando comando de cambio de baud rate...")
        ser.write(ubx_set_baud)
        time.sleep(1)
        
        # Cerrar y reabrir con el nuevo baud rate
        ser.close()
        time.sleep(1)
        
        print(f"Reconectando a {port} con 115200 baudios...")
        ser = serial.Serial(port, 115200, timeout=1)
        
        # Verificar la conexión
        time.sleep(1)
        if ser.in_waiting:
            response = ser.readline().decode('ascii', errors='replace').strip()
            print(f"Respuesta recibida: {response}")
            print("¡Cambio de baud rate exitoso!")
        
        ser.close()
        
    except Exception as e:
        print(f"Error: {e}")
        if 'ser' in locals():
            ser.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Configura el Módulo GPS")
    parser.add_argument(
        "--port", 
        type=str, 
        default="COM26",
        help="Puerto serie (default: COM26)"
    )
    parser.add_argument(
        "--initial-baud",
        type=int,
        default=9600,
        help="Baud rate inicial (default: 9600)"
    )
    
    args = parser.parse_args()
    
    configure_gps(args.port, args.initial_baud) 