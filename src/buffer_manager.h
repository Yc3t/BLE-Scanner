#ifndef BUFFER_MANAGER_H
#define BUFFER_MANAGER_H

#include "ble_scanner.h"

/* Hash Table Configuration */
#define HASH_SIZE       64    /* Power of 2, > 4/3 * MAX_DEVICES */
#define HASH_MASK       (HASH_SIZE - 1)

/* Buffer States */
enum buffer_state {
    BUFFER_EMPTY,      /* Buffer is empty/unused */
    BUFFER_FILLING,    /* Currently collecting data */
    BUFFER_READY,      /* Ready for transmission */
    BUFFER_SENDING     /* Being transmitted */
};

/* Hash Table Entry States */
enum entry_state {
    ENTRY_EMPTY,       /* Slot never used */
    ENTRY_OCCUPIED,    /* Contains valid data */
    ENTRY_DELETED      /* Previously used, now deleted */
};

/* Hash Table Entry Structure */
struct hash_entry {
    enum entry_state state;
    struct device_data device;
};

/* Buffer Structure */
struct ble_buffer {
    struct buffer_header header;
    struct hash_entry hash_table[HASH_SIZE];
    uint16_t hash_entries;
    enum buffer_state state;
    struct k_sem lock;        /* Buffer access semaphore */
};

/* Double Buffer Manager */
struct buffer_manager {
    struct ble_buffer buffers[2];  /* Double buffer */
    uint8_t active_buffer;         /* Current active buffer index */
    struct k_sem switch_lock;      /* Buffer switching semaphore */
    uint8_t msg_sequence;          /* Global message sequence counter */
};

/* Function Declarations */
int buffer_manager_init(void);
struct ble_buffer *get_active_buffer(void);
void switch_buffers(void);
struct device_data *find_or_add_device(const bt_addr_le_t *addr, struct ble_buffer *buffer);
void reset_buffer(struct ble_buffer *buffer);
struct buffer_manager *get_buffer_manager(void);

#endif /* BUFFER_MANAGER_H */