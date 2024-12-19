import pandas as pd
import pymongo
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def connect_mongodb(uri="mongodb://localhost:27017/"):
    client = pymongo.MongoClient(uri)
    return client.ble_scanner.adv_buffer1

def query_data_by_date(collection, start_date, end_date):
    query = {
        "timestamp": {
            "$gte": start_date,
            "$lte": end_date
        }
    }
    return list(collection.find(query))

def process_buffer_data(data):
    """
    Process buffer data and create a normalized DataFrame
    """
    records = []
    for buffer in data:
        base_info = {
            'timestamp': buffer['timestamp'],
            'sequence': buffer['sequence'],
            'n_adv_raw': buffer['n_adv_raw'],
            'n_mac': buffer['n_mac']
        }
        
        for device in buffer['devices']:
            record = base_info.copy()
            record.update(device)
            records.append(record)
    
    df = pd.DataFrame(records)
    df['hour'] = df['timestamp'].dt.hour
    df['minute'] = df['timestamp'].dt.minute
    df['day'] = df['timestamp'].dt.date
    df['weekday'] = df['timestamp'].dt.day_name()
    return df

def get_temporal_analysis(df):
    """
    Perform temporal analysis of the data
    """
    temporal_stats = {
        'total_intervals': df['sequence'].nunique(),
        'time_span': (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600,
        'avg_devices_per_interval': df.groupby('sequence')['mac'].nunique().mean(),
        'total_unique_devices': df['mac'].nunique(),
        'hourly_pattern': df.groupby('hour')['mac'].nunique().to_dict(),
        'daily_pattern': df.groupby('day')['mac'].nunique().to_dict()
    }
    return temporal_stats

def get_device_analysis(df):
    """
    Perform device-specific analysis
    """
    device_stats = {
        'top_devices': df['mac'].value_counts().head(10).to_dict(),
        'addr_type_dist': df['addr_type'].value_counts().to_dict(),
        'adv_type_dist': df['adv_type'].value_counts().to_dict(),
        'rssi_stats': {
            'mean': df['rssi'].mean(),
            'std': df['rssi'].std(),
            'min': df['rssi'].min(),
            'max': df['rssi'].max()
        }
    }
    return device_stats

def plot_temporal_patterns(df):
    """
    Create temporal visualization plots
    """
    fig, axes = plt.subplots(2, 2, figsize=(20, 15))
    
    # Hourly pattern
    hourly_devices = df.groupby('hour')['mac'].nunique()
    sns.lineplot(data=hourly_devices, ax=axes[0,0])
    axes[0,0].set_title('Unique Devices by Hour')
    axes[0,0].set_xlabel('Hour')
    axes[0,0].set_ylabel('Number of Unique Devices')
    
    # Daily pattern
    daily_devices = df.groupby('day')['mac'].nunique()
    sns.lineplot(data=daily_devices, ax=axes[0,1])
    axes[0,1].set_title('Unique Devices by Day')
    axes[0,1].set_xlabel('Date')
    axes[0,1].set_ylabel('Number of Unique Devices')
    plt.xticks(rotation=45)
    
    # RSSI distribution
    sns.histplot(data=df, x='rssi', ax=axes[1,0], bins=50)
    axes[1,0].set_title('RSSI Distribution')
    axes[1,0].set_xlabel('RSSI (dBm)')
    
    # Device presence heatmap
    presence_matrix = df.pivot_table(
        index='hour',
        columns='day',
        values='mac',
        aggfunc='nunique'
    )
    sns.heatmap(presence_matrix, ax=axes[1,1], cmap='YlOrRd')
    axes[1,1].set_title('Device Presence Heatmap')
    
    plt.tight_layout()
    return fig

def plot_device_patterns(df):
    """
    Create device-specific visualization plots
    """
    fig, axes = plt.subplots(2, 2, figsize=(20, 15))
    
    # Top devices by frequency
    top_devices = df['mac'].value_counts().head(10)
    sns.barplot(x=top_devices.values, y=top_devices.index, ax=axes[0,0])
    axes[0,0].set_title('Top 10 Most Frequent Devices')
    axes[0,0].set_xlabel('Number of Appearances')
    
    # Address type distribution
    sns.countplot(data=df, x='addr_type', ax=axes[0,1])
    axes[0,1].set_title('Address Type Distribution')
    
    # Advertisement type distribution
    sns.countplot(data=df, x='adv_type', ax=axes[1,0])
    axes[1,0].set_title('Advertisement Type Distribution')
    
    # RSSI by device type
    sns.boxplot(data=df, x='addr_type', y='rssi', ax=axes[1,1])
    axes[1,1].set_title('RSSI Distribution by Address Type')
    
    plt.tight_layout()
    return fig

def export_analysis(df, filename="ble_analysis.html"):
    """
    Export analysis to HTML report
    """
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    # Create interactive visualizations
    temporal_fig = make_subplots(rows=2, cols=2)
    
    # Add traces
    temporal_fig.add_trace(
        go.Scatter(
            x=df.groupby('hour')['mac'].nunique().index,
            y=df.groupby('hour')['mac'].nunique().values,
            name="Hourly Pattern"
        ),
        row=1, col=1
    )
    
    # Add more interactive plots...
    
    # Save to HTML
    temporal_fig.write_html(filename) 