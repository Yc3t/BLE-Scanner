-- Tabla para estadísticas del scanner BLE
CREATE TABLE IF NOT EXISTS ble_scanner_stats (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    period_start TIMESTAMP NOT NULL,
    total_devices INTEGER NOT NULL,
    stats_json JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para optimizar consultas
CREATE INDEX idx_ble_stats_timestamp ON ble_scanner_stats(timestamp);
CREATE INDEX idx_ble_stats_period ON ble_scanner_stats(period_start); 