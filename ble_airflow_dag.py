from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mongo.hooks.mongo import MongoHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import pandas as pd
import json

# DAG default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Create DAG
dag = DAG(
    'ble_scanner_pipeline',
    default_args=default_args,
    description='Pipeline para procesar datos del scanner BLE',
    schedule_interval=timedelta(hours=1),  # Ejecutar cada hora
    catchup=False
)

def extract_from_mongodb(**context):
    """Extrae datos recientes de MongoDB."""
    mongo_hook = MongoHook(mongo_conn_id='mongo_default')
    
    # Obtiene datos de la última hora
    last_hour = datetime.now() - timedelta(hours=1)
    
    query = {
        "timestamp": {"$gte": last_hour}
    }
    
    collection = mongo_hook.get_collection(
        mongo_collection='advertisements',
        mongo_db='ble_scanner'
    )
    
    # Extrae documentos
    documents = list(collection.find(query))
    
    # Guarda los datos en XCom para el siguiente task
    context['task_instance'].xcom_push(key='raw_data', value=documents)
    
    return f"Extraídos {len(documents)} documentos"

def process_data(**context):
    """Procesa y analiza los datos del scanner."""
    # Obtiene datos del task anterior
    documents = context['task_instance'].xcom_pull(key='raw_data')
    
    # Convierte a DataFrame para análisis
    df = pd.DataFrame(documents)
    
    # Análisis por dispositivo
    device_stats = df.groupby('mac_address').agg({
        'rssi': ['mean', 'min', 'max', 'count'],
        'timestamp': ['min', 'max']
    }).reset_index()
    
    # Calcula tiempo de presencia
    device_stats['duration'] = device_stats[('timestamp', 'max')] - device_stats[('timestamp', 'min')]
    
    # Prepara resultados para almacenar
    results = {
        'timestamp': datetime.now(),
        'period_start': last_hour,
        'total_devices': len(device_stats),
        'device_details': device_stats.to_dict('records')
    }
    
    # Pasa resultados al siguiente task
    context['task_instance'].xcom_push(key='processed_data', value=results)
    
    return "Datos procesados exitosamente"

def load_to_warehouse(**context):
    """Carga resultados procesados en el data warehouse."""
    # Obtiene datos procesados
    results = context['task_instance'].xcom_pull(key='processed_data')
    
    # Conexión a PostgreSQL (data warehouse)
    pg_hook = PostgresHook(postgres_conn_id='postgres_dw')
    
    # Inserta resumen en tabla de estadísticas
    pg_hook.run("""
        INSERT INTO ble_scanner_stats 
        (timestamp, period_start, total_devices, stats_json)
        VALUES (%s, %s, %s, %s)
    """, parameters=(
        results['timestamp'],
        results['period_start'],
        results['total_devices'],
        json.dumps(results['device_details'])
    ))
    
    return "Datos cargados en el warehouse"

# Define tasks
extract_task = PythonOperator(
    task_id='extract_from_mongodb',
    python_callable=extract_from_mongodb,
    provide_context=True,
    dag=dag,
)

process_task = PythonOperator(
    task_id='process_data',
    python_callable=process_data,
    provide_context=True,
    dag=dag,
)

load_task = PythonOperator(
    task_id='load_to_warehouse',
    python_callable=load_to_warehouse,
    provide_context=True,
    dag=dag,
)

# Define task dependencies
extract_task >> process_task >> load_task 