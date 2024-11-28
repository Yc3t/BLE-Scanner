
# BLE Scanner Data Pipeline

Este proyecto implementa un sistema completo de escaneo BLE (Bluetooth Low Energy) con procesamiento y almacenamiento de datos. El sistema consta de tres componentes principales:

1. Scanner BLE (Zephyr RTOS)
2. Recolector de datos con MongoDB
3. Pipeline de procesamiento con Apache Airflow

## Arquitectura del Sistema

```ascii
[Scanner BLE (nRF52840)] --> UART --> [Recolector Python/MongoDB] --> [Airflow Pipeline] --> [Data Warehouse]
```

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

- Lee datos del puerto serie
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

### 3. Pipeline de Datos (ble_airflow_dag.py)

DAG de Apache Airflow que:

- Extrae datos de MongoDB
- Procesa y analiza datos de dispositivos BLE
- Carga resultados en un data warehouse

#### Requisitos
- Apache Airflow
- Conectores de Airflow para MongoDB y PostgreSQL

#### Configuración
1. Instalar dependencias de Airflow:
```bash
pip install apache-airflow apache-airflow-providers-mongo apache-airflow-providers-postgres
```

2. Configurar conexiones en Airflow:
   - `mongo_default`: Conexión a MongoDB
   - `postgres_dw`: Conexión al data warehouse

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

### 3. Configurar Airflow

1. Copiar el DAG:
```bash
cp ble_airflow_dag.py $AIRFLOW_HOME/dags/
```

2. Iniciar Airflow:
```bash
airflow scheduler
airflow webserver
```

## Estructura de Datos

### Formato UART
- Header: `0x55 0x55 0x55 0x55`
- Tipo de mensaje: `0x01` (Advertisement)
- Número de secuencia: 1 byte
- Datos de advertisement: 43 bytes

### Colección MongoDB
- timestamp
- mac_address
- rssi
- raw_data
- metadata

### Data Warehouse
- Estadísticas agregadas por dispositivo
- Análisis temporal
- Métricas de presencia

