#include "buffer_manager.h"
LOG_MODULE_DECLARE(ble_scanner);

static struct buffer_manager buffer_mgr;


//hash from mac address

static uint32_t hash_mac(const uint8_t *mac){
    uint32_t hash = 0;
    for (int i = 0; i<6; i++){
        hash = (hash <<5) + hash + mac[i];
    }

    return hash & HASH_MASK;
}

//init buffer manager

int buffer_manager_init(void){
    //buffer switching semaphore
    k_sem_init(&buffer_mgr.switch_lock,1,1);
    buffer_mgr.msg_sequence = 0;

    //initialize both buffers
    for (int i=0; i<2; i++){
        struct ble_buffer *buf = &buffer_mgr.buffers[i];


        //initialize buffer semaphore
        k_sem_init(&buf->lock,1,1);


        //clear buffer contents 
        memset(&buf->header,0,sizeof(struct buffer_header));
        memset(&buf -> hash_table,0,sizeof(buf->hash_table));
        
        //initial state
        buf->state = BUFFER_EMPTY;
        buf->hash_entries =0;
        //initialize header magic pattern
        memset(buf->header.magic, UART_HEADER_MAGIC,4);

    }

    //set initial active buffer
    buffer_mgr.active_buffer = 0
    buffer_mgr.buffers[0].state = BUFFER_FILLING;
    return 0;

}

//get current active buffer

struct ble_buffer *get_active_buffer(void){
    return &buffer_mgr.buffers[buffer_mgr.active_buffer];
}

//switch between buffers
void switch_buffers(void){
    k_sem_take(&buffer_mgr.switch_lock,K_FOREVER);


    //get current buffer
    struct ble_buffer *current_bfr = get_active_buffer()


    //if current buffer has data, mark it as ready
    if (current_bfr->hash_entries > 0){
        k_sem_take(&current_bfr->lock,K_FOREVER);
        current_bfr->state = BUFFER_READY;
        current_bfr->header.sequence = buffer_mgr.msg_sequence++;
        current_bfr->header.timestamp = k_uptime_get_32();
        k_sem_give(&current->lock);
    }

    //switch to other buffer

    buffer_mgr.active_buffer = (buffer_mgr.active_buffer + 1) % 2;
    struct ble_buffer *next = get_active_buffer();

    //reset next buffer if its not being sent

    if (next->state !=BUFFER_SENDING){
        reset_buffer(next)
    }else{
        LOG_WRN("The other buffer is still sending");
    }

    k_sem_give(&buffer_mgr.switch_lock);

}

void reset_buffer (struct ble_buffer *buffer){
    k_sem_take(&buffer->lock, FOREVER);

    //clear header

    memset(&buffer->header, 0,sizeof(struct buffer_header));
    memset(buffer->header.magic,UART_HEADER_MAGIC,4);

    //clear hash
    memset(buffer->hash_table,0,sizeof(buffer->hash_table));

    //reset counters and state
    buffer->hash_entries = 0;
    buffer->state=BUFFER_FILLING;

    k_sem_give(&buffer->lock);

}

//find or add device to the hash table
struct device_data *find_or_add_device(const bt_addr_le_t *addr, struct ble_buffer *buffer){
    uint32_t index = hash_mac(addr->a.val);
    uint32_t original_index = index;

    do
    {
        struct hash_entry *entry = &buffer ->hash_table[index];

        //check if device already exists
        if (entry ->state == ENTRY_OCCUPIED && memcmp(entry->device.addr, addr->a.val,6) == 0){
            return &entry->device;

        }

        //look for empty slot
        if (entry-> state != ENTRY_OCCUPIED){
            //check limits
            if(buffer ->hash_entries >= MAX_DEVICES){
                LOG_WRN("MAX DEVICES REACHED!");
                return NULL;
            }

            //add new device

            entry->state = ENTRY_OCCUPIED;
            memcpy(entry->device.addr, addr.>a.val,6);
            entry->device.last_seen = k_uptime_get_32();
            buffer->hash_entries++;
            buffer->header.n_mac++;

            return &entry->device;


        index = (index+1) & HASH_MASK;



    } while (index != original_index);

    LOG_WRN("Hash table full!");
    return NULL;
    
}

