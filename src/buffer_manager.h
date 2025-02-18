#ifndef BUFFER_MANAGER_H
#define BUFFER_MANAGER_H

#include "ble_scanner.h"

#define HASH_SIZE   64
#define HASH_MASK   (HASH_SIZE-1)


enum buffer_state{
    BUFFER_EMPTY,
    BUFFER_FILLING,
    BUFFER_READY,
    BUFFER_SENDING
}

enum entry_state{
    ENTRY_EMPTY,
    ENTRY_OCCUPIED,
    ENTRY_DELETED 
}

struct hash_entry {
    enum entry_state state;
    enum device_data device;
}


//buffer structure
struct ble_buffer{
    struct buffer_header header;
    struct hash_entry hash_table[HASH_SIZE];
    uint16_t hash_entries;
    enum buffer_state state;
    struct k_sem lock;

}

// double buffer

struct buffer_manager {
    struct ble_buffer buffers[2];
    uint8_t active_buffer;
    struct k_sem switch_lock;
    uint8_t msg_sequence;



//functions we need
int buffer_manager_init(void);
struct ble_buffer *get_active_buffer(void);
struct device_data *find_or_add_device(const bt_addr_le_t *addr, struct ble_buffer *buffer);
void reset_buffer (struct ble_buffer *buffer);

#endif




