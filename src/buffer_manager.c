#include "buffer_manager.h"

LOG_MODULE_DECLARE(ble_scanner);

static struct buffer_manager buffer_mgr;

/* Get buffer manager instance */
struct buffer_manager *get_buffer_manager(void) {
    return &buffer_mgr;
}

/* Calculate hash from MAC address */
static uint32_t hash_mac(const uint8_t *mac) {
    uint32_t hash = 0;
    for (int i = 0; i < 6; i++) {
        hash = (hash << 5) + hash + mac[i];  // hash * 33 + mac[i]
    }
    return hash & HASH_MASK;
}

/* Initialize the buffer manager */
int buffer_manager_init(void) {
    // Initialize buffer switching semaphore
    k_sem_init(&buffer_mgr.switch_lock, 1, 1);
    buffer_mgr.msg_sequence = 0;
    
    // Initialize both buffers
    for (int i = 0; i < 2; i++) {
        struct ble_buffer *buf = &buffer_mgr.buffers[i];
        
        // Initialize buffer semaphore
        k_sem_init(&buf->lock, 1, 1);
        
        // Clear buffer contents
        memset(&buf->header, 0, sizeof(struct buffer_header));
        memset(buf->hash_table, 0, sizeof(buf->hash_table));
        
        // Set initial state
        buf->state = BUFFER_EMPTY;
        buf->hash_entries = 0;
        
        // Initialize header magic pattern
        memset(buf->header.magic, UART_HEADER_MAGIC, 4);
    }
    
    // Set initial active buffer
    buffer_mgr.active_buffer = 0;
    buffer_mgr.buffers[0].state = BUFFER_FILLING;
    
    return 0;
}

/* Get the currently active buffer */
struct ble_buffer *get_active_buffer(void) {
    return &buffer_mgr.buffers[buffer_mgr.active_buffer];
}

/* Switch between buffers */
void switch_buffers(void) {
    k_sem_take(&buffer_mgr.switch_lock, K_FOREVER);
    
    // Get current buffer
    struct ble_buffer *current = get_active_buffer();
    
    // If current buffer has data, mark it as ready
    if (current->hash_entries > 0) {
        k_sem_take(&current->lock, K_FOREVER);
        current->state = BUFFER_READY;
        current->header.sequence = buffer_mgr.msg_sequence++;
        current->header.timestamp = k_uptime_get_32();
        k_sem_give(&current->lock);
    }
    
    // Switch to other buffer
    buffer_mgr.active_buffer = (buffer_mgr.active_buffer + 1) % 2;
    struct ble_buffer *next = get_active_buffer();
    
    // Reset next buffer if it's not being sent
    if (next->state != BUFFER_SENDING) {
        reset_buffer(next);
    } else {
        LOG_WRN("Buffer switch delayed - other buffer still sending");
    }
    
    k_sem_give(&buffer_mgr.switch_lock);
}

/* Reset a buffer to initial state */
void reset_buffer(struct ble_buffer *buffer) {
    k_sem_take(&buffer->lock, K_FOREVER);
    
    // Clear header
    memset(&buffer->header, 0, sizeof(struct buffer_header));
    memset(buffer->header.magic, UART_HEADER_MAGIC, 4);
    
    // Clear hash table
    memset(buffer->hash_table, 0, sizeof(buffer->hash_table));
    
    // Reset counters and state
    buffer->hash_entries = 0;
    buffer->state = BUFFER_FILLING;
    
    k_sem_give(&buffer->lock);
}

/* Find or add a device to the buffer's hash table */
struct device_data *find_or_add_device(const bt_addr_le_t *addr, 
                                     struct ble_buffer *buffer) {
    uint32_t index = hash_mac(addr->a.val);
    uint32_t original_index = index;
    
    do {
        struct hash_entry *entry = &buffer->hash_table[index];
        
        // Check if device already exists
        if (entry->state == ENTRY_OCCUPIED &&
            memcmp(entry->device.addr, addr->a.val, 6) == 0) {
            return &entry->device;
        }
        
        // Look for empty or deleted slot
        if (entry->state != ENTRY_OCCUPIED) {
            // Check limits
            if (buffer->hash_entries >= MAX_DEVICES) {
                LOG_WRN("Maximum devices reached");
                return NULL;
            }
            
            // Add new device
            entry->state = ENTRY_OCCUPIED;
            memcpy(entry->device.addr, addr->a.val, 6);
            entry->device.n_adv = 0;
            entry->device.last_seen = k_uptime_get_32();
            buffer->hash_entries++;
            buffer->header.n_mac++;
            
            return &entry->device;
        }
        
        // Try next slot
        index = (index + 1) & HASH_MASK;
    } while (index != original_index);
    
    LOG_WRN("Hash table full");
    return NULL;
}