import pandas as pd
import pymongo
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def connect_mongodb(uri="mongodb://localhost:27017/", db_name="ble_scanner", collection_name="adv_buffer1"):
    """
    Connect to MongoDB and return specified collection
    
    Args:
        uri (str): MongoDB connection URI
        db_name (str): Name of the database
        collection_name (str): Name of the collection
    
    Returns:
        Collection: MongoDB collection object
    """
    client = pymongo.MongoClient(uri)
    db = client[db_name]
    return db[collection_name]

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

def analyze_buffer_stats(data, df):
    """
    Analyze buffer statistics and create visualization
    
    Args:
        data (list): Raw buffer data from MongoDB
        df (DataFrame): Processed DataFrame with buffer data
    
    Returns:
        tuple: (stats_dict, figure)
    """
    # Calculate basic statistics
    stats = {
        'total_buffers': len(data),
        'total_devices': df['mac'].nunique(),
        'total_advertisements': df['n_adv_raw'].sum(),
        'avg_devices_per_buffer': sum(len(buffer['devices']) for buffer in data) / len(data),
        'avg_rssi': df['rssi'].mean(),
        'time_span_hours': (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600
    }
    
    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Get sequence numbers and timestamps
    sequences = df['sequence'].unique()
    timestamps = df.groupby('sequence')['timestamp'].first()
    devices_per_buffer = df.groupby('sequence')['mac'].nunique()
    
    # Plot 1: Devices per buffer with sequence gaps highlighted
    ax1.plot(sequences, devices_per_buffer.values, 
            marker='o', linestyle='-', color='blue', label='Devices')
    
    # Highlight sequence gaps
    prev_seq = sequences[0]
    for seq in sequences[1:]:
        if seq - prev_seq > 1:
            ax1.axvspan(prev_seq, seq, color='red', alpha=0.2)
            ax1.text((prev_seq + seq)/2, ax1.get_ylim()[1], 
                    f'Gap\n({seq-prev_seq-1})', 
                    ha='center', va='bottom')
        prev_seq = seq
    
    ax1.set_title('Devices per Buffer with Sequence Gaps')
    ax1.set_xlabel('Buffer Sequence')
    ax1.set_ylabel('Number of Devices')
    ax1.grid(True)
    
    # Plot 2: Time between buffers
    time_diffs = timestamps.diff().dt.total_seconds()
    ax2.plot(sequences[1:], time_diffs[1:], 
            marker='o', linestyle='-', color='green', label='Time Interval')
    ax2.set_title('Time Between Consecutive Buffers')
    ax2.set_xlabel('Buffer Sequence')
    ax2.set_ylabel('Time (seconds)')
    ax2.grid(True)
    
    # Add statistics to the plot
    stats_text = (
        f"Total Buffers: {stats['total_buffers']}\n"
        f"Total Unique Devices: {stats['total_devices']}\n"
        f"Avg Devices/Buffer: {stats['avg_devices_per_buffer']:.2f}\n"
        f"Time Span: {stats['time_span_hours']:.2f} hours\n"
        f"Avg RSSI: {stats['avg_rssi']:.1f} dBm"
    )
    
    # Add text box with statistics
    plt.figtext(1.02, 0.7, stats_text, 
                bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray'),
                fontsize=10)
    
    plt.tight_layout()
    
    # Calculate additional sequence statistics
    sequence_gaps = []
    prev_seq = sequences[0]
    for seq in sequences[1:]:
        if seq - prev_seq > 1:
            sequence_gaps.append((prev_seq, seq, seq-prev_seq-1))
        prev_seq = seq
    
    if sequence_gaps:
        stats['sequence_gaps'] = sequence_gaps
        stats['total_gaps'] = len(sequence_gaps)
        stats['total_missed_sequences'] = sum(gap[2] for gap in sequence_gaps)
    else:
        stats['sequence_gaps'] = []
        stats['total_gaps'] = 0
        stats['total_missed_sequences'] = 0
    
    return stats, fig 