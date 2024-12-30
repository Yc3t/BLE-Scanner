import serial
import time

def configure_gps(port="COM26", baudrate=9600):
    try:
        # Abrimos el puerto serial con el baud rate por defecto
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"Conectado al GPS en {port} con {baudrate} baudios")
        
        # Comandos para enviar
        commands = [
            # Ajustar la tasa de refreso a 1Hz
            "$PMTK220,1000*1F",
            # 115200 baud rate
            "$PMTK251,115200*1F"
        ]

        # Enviamos cada comandod
        for cmd in commands:
            print(f"\nSending: {cmd}")
            ser.write((cmd + '\r\n').encode())
            time.sleep(1)  # Esperamos a que el comando se procese
            
            # Leer la respuesta
            while ser.in_waiting:
                response = ser.readline().decode('ascii', errors='replace').strip()
                print(f"Response: {response}")

        print("\nConfiguración Completada!")
        
        # Cerrar la conexión
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