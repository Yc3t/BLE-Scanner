def calculate_uart_time(n_devices=50):
    header_size = 7  # bytes
    device_size = 42  # bytes per device
    total_bytes = header_size + (device_size * n_devices)
    
    # Cada byte necesita 10 bits (8 datos + 1 start + 1 stop)
    total_bits = total_bytes * 10
    
    # Tiempo en segundos a 115200 baud
    uart_time = total_bits / 115200
    return uart_time

# Para buffer lleno
uart_time = calculate_uart_time(50)
print(f"Tiempo UART para buffer lleno: {uart_time:.3f} segundos")
