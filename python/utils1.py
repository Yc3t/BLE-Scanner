import pandas as pd
import pymongo
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

def connect_mongodb(uri="mongodb://localhost:27017/"):
    client = pymongo.MongoClient(uri)
    return client.ble_scanner.adv_5_min

# Función para consultar datos por rango de fechas
def query_data_by_date(collection, start_date, end_date):
    query = {
        "timestamp": {
            "$gte": start_date,
            "$lte": end_date
        }
    }
    return list(collection.find(query))

def basic_analysis(df, start_date, end_date):
    print(f"Análisis para el período: {start_date} a {end_date}")
    print("-" * 50)
    
    # 1. Número total de muestras
    total_samples = len(df)
    print(f"Número total de muestras: {total_samples}")
    
    # 2. Número de MACs distintas
    unique_macs = df['mac'].nunique()
    print(f"Número de MACs distintas: {unique_macs}")
    
    # 3. Listado de MACs y frecuencia
    mac_counts = df['mac'].value_counts()
    print("\nTop 10 MACs más frecuentes:")
    print(mac_counts.head(10))
    
    # 4. Chequeo de secuencia
    sequence_gaps = check_sequence_gaps(df)
    if sequence_gaps:
        print("\nPérdidas de secuencia detectadas:")
        for gap in sequence_gaps[:10]:  # Mostrar solo los primeros 10 gaps
            print(f"Salto de secuencia: {gap['from']} -> {gap['to']}")
    else:
        print("\nNo se detectaron pérdidas de secuencia")
    
    # Visualización de datos
    plt.figure(figsize=(12, 6))
    df['timestamp'].hist(bins=50)
    plt.title('Distribución temporal de las muestras')
    plt.xlabel('Timestamp')
    plt.ylabel('Frecuencia')
    plt.show()
    
    return {
        'total_samples': total_samples,
        'unique_macs': unique_macs,
        'mac_counts': mac_counts,
        'sequence_gaps': sequence_gaps
    }

def check_sequence_gaps(df):
    gaps = []
    df_sorted = df.sort_values('timestamp')
    
    prev_seq = None
    for _, row in df_sorted.iterrows():
        curr_seq = row['sequence']
        
        if prev_seq is not None:
            expected_seq = (prev_seq + 1) % 256
            if curr_seq != expected_seq:
                gaps.append({
                    'from': prev_seq,
                    'to': curr_seq,
                    'timestamp': row['timestamp']
                })
        prev_seq = curr_seq
    
    return gaps
def export_to_csv(data, filename="ble_data2.csv"):
    """
    Convierte los datos de MongoDB a un DataFrame y los exporta a CSV
    Args:
        data: Lista de documentos de MongoDB
        filename: Nombre del archivo CSV a crear
    Returns:
        DataFrame con los datos
    """
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"Datos exportados a {filename}")
    return df