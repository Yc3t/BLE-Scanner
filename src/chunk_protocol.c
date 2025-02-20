#include "chunk_protocol.h"
#include "uart_handler.h"

LOG_MODULE_DECLARE(ble_scanner);

/* Calculate CRC16 for data verification */
uint16_t calculate_crc16(const uint8_t *data, size_t length) {
    uint16_t crc = 0xFFFF;
    
    for (size_t i = 0; i < length; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 1) {
                crc = (crc >> 1) ^ 0xA001;
            } else {
                crc = crc >> 1;
            }
        }
    }
    
    return crc;
}

/* Send a single chunk with retries */
static bool send_chunk(const struct chunk *chunk) {
    for (int retry = 0; retry < MAX_RETRIES; retry++) {
        // Send header
        uart_write_bytes((uint8_t*)&chunk->header, 
                        sizeof(struct chunk_header));
        
        // Send device data
        size_t data_size = chunk->header.n_devices * sizeof(struct device_data);
        uart_write_bytes((uint8_t*)chunk->devices, data_size);
        
        // Send CRC
        uart_write_bytes((uint8_t*)&chunk->crc, sizeof(uint16_t));
        
        // Wait for acknowledgment
        if (uart_wait_ack(chunk->header.sequence)) {
            return true;
        }
        
        LOG_WRN("Retry %d for chunk %d", retry + 1, chunk->header.sequence);
        k_sleep(K_MSEC(10));
    }
    
    return false;
}

/* Send complete buffer in chunks */
void send_buffer_chunked(struct ble_buffer *buffer) {
    k_sem_take(&buffer->lock, K_FOREVER);
    
    if (buffer->hash_entries == 0) {
        k_sem_give(&buffer->lock);
        return;
    }
    
    uint16_t devices_sent = 0;
    uint8_t chunk_sequence = 0;
    uint16_t hash_index = 0;
    
    struct chunk current_chunk;
    memset(&current_chunk, 0, sizeof(struct chunk));
    
    // Process all devices in hash table
    while (devices_sent < buffer->hash_entries) {
        // Prepare chunk header
        current_chunk.header.start_marker = UART_HEADER_MAGIC;
        current_chunk.header.sequence = chunk_sequence++;
        current_chunk.header.total_devices = buffer->hash_entries;
        current_chunk.header.chunk_offset = devices_sent / MAX_DEVICES_PER_CHUNK;
        
        // Set chunk type
        if (devices_sent == 0) {
            current_chunk.header.type = CHUNK_TYPE_START;
        } else if (devices_sent + MAX_DEVICES_PER_CHUNK >= buffer->hash_entries) {
            current_chunk.header.type = CHUNK_TYPE_END;
        } else {
            current_chunk.header.type = CHUNK_TYPE_DATA;
        }
        
        // Fill chunk with devices
        uint8_t devices_in_chunk = 0;
        while (devices_in_chunk < MAX_DEVICES_PER_CHUNK && 
               devices_sent < buffer->hash_entries) {
            // Find next occupied entry
            while (hash_index < HASH_SIZE && 
                   buffer->hash_table[hash_index].state != ENTRY_OCCUPIED) {
                hash_index++;
            }
            
            if (hash_index < HASH_SIZE) {
                // Copy device data
                memcpy(&current_chunk.devices[devices_in_chunk],
                       &buffer->hash_table[hash_index].device,
                       sizeof(struct device_data));
                devices_in_chunk++;
                devices_sent++;
                hash_index++;
            }
        }
        
        current_chunk.header.n_devices = devices_in_chunk;
        
        // Calculate CRC
        current_chunk.crc = calculate_crc16((uint8_t*)&current_chunk,
                                          sizeof(struct chunk_header) + 
                                          (devices_in_chunk * sizeof(struct device_data)));
        
        // Send chunk
        if (!send_chunk(&current_chunk)) {
            LOG_ERR("Failed to send chunk %d", current_chunk.header.sequence);
            k_sem_give(&buffer->lock);
            return;
        }
    }
    
    k_sem_give(&buffer->lock);
}