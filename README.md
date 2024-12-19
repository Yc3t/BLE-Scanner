# BLE Scanner 

Este proyecto implementa un sistema de escaneo BLE (Bluetooth Low Energy) con almacenamiento de datos. El sistema consta de dos componentes principales:

1. Scanner BLE (Zephyr RTOS)
2. Recolector de datos con MongoDB



## Componentes

### 1. Scanner BLE (main.c)

Implementado en un microcontrolador nRF52840 usando Zephyr RTOS, este componente:

- Realiza escaneo pasivo de dispositivos BLE
- Captura datos de advertisement incluyendo:
  - Dirección MAC
  - RSSI
  - Datos raw del advertisement
  - Timestamp
- Transmite datos por UART usando un protocolo binario personalizado

#### Requisitos de Hardware
- nRF52840 DK o compatible
- Conexión UART a PC host

### 2. Recolector de Datos (uart-mongo.py)

Script Python que:

- Lee datos del puerto serie usando uart.py
- Decodifica el protocolo binario
- Almacena datos en MongoDB
- Proporciona estadísticas en tiempo real

#### Requisitos
- Python 3.7+
- MongoDB
- PySerial
- PyMongo

#### Instalación
```bash
pip install pyserial pymongo
```

#### Uso
```bash
python uart-mongo.py --port /dev/ttyUSB0 --mongo mongodb://localhost:27017/
```

## Configuración del Proyecto

### 1. Compilar el Firmware

```bash
west build -b nrf52840dk_nrf52840
west flash
```

### 2. Iniciar el Recolector

```bash
python uart-mongo.py --port /dev/ttyUSB0
```

## Estructura de Datos

### Formato UART
- Header: `0x55 0x55 0x55 0x55`
- Tipo de mensaje: `0x01` (Advertisement)
- Número de secuencia: 1 byte
- Datos de advertisement: 43 bytes

### Colección MongoDB
```json
{
    "timestamp": "ISODate",
    "sequence": "int",
    "mac": "string",
    "addr_type": "int",
    "adv_type": "int",
    "rssi": "int",
    "data_len": "int",
    "data": "hex string"
}
```
