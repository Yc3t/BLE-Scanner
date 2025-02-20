#include "ble_scanner.h"
#include "buffer_manager.h"
#include "chunk_protocol.h"
#include "uart_handler.h"

LOG_MODULE_REGISTER(ble_scanner, LOG_LEVEL_INF);

/* Work item for buffer switching */
static struct k_work_delayable buffer_switch_work;

/* BLE scanning parameters */
static struct bt_le_scan_param scan_param = {
    .type = BT_LE_SCAN_TYPE_PASSIVE,
    .options = BT_LE_SCAN_OPT_NONE,
    .interval = BT_GAP_ADV_FAST_INT_MIN_2,
    .window = BT_GAP_ADV_FAST_INT_MIN_2
};

/* Work item for UART sending */
static struct k_work uart_send_work;
static struct ble_buffer *sending_buffer = NULL;

/* BLE scanning callback */
static void scan_cb(const bt_addr_le_t *addr, int8_t rssi,
                   uint8_t adv_type, struct net_buf_simple *buf) {
    struct ble_buffer *active = get_active_buffer();
    
    if (active->state != BUFFER_FILLING) {
        return;
    }

    k_sem_take(&active->lock, K_FOREVER);
    
    // Update raw advertisement counter
    active->header.n_adv_raw++;
    
    // Find or add device to hash table
    struct device_data *device = find_or_add_device(addr, active);
    if (device) {
        // Update device data
        device->addr_type = addr->type;
        device->adv_type = adv_type;
        device->rssi = rssi;
        device->data_len = MIN(buf->len, sizeof(device->data));
        memcpy(device->data, buf->data, device->data_len);
        device->n_adv++;
        device->last_seen = k_uptime_get_32();
        
        // If buffer is full, trigger early switch
        if (active->hash_entries >= MAX_DEVICES) {
            k_work_reschedule(&buffer_switch_work, K_NO_WAIT);
        }
    }
    
    k_sem_give(&active->lock);
}

/* Buffer switch work handler */
static void buffer_switch_handler(struct k_work *work) {
    switch_buffers();
    
    // Schedule next switch
    k_work_reschedule(&buffer_switch_work, 
                      K_MSEC(SAMPLING_INTERVAL_MS));
    
    // Trigger send work for the filled buffer
    k_work_submit(&uart_send_work);
}

/* UART send work handler */
static void uart_send_handler(struct k_work *work) {
    struct buffer_manager *mgr = get_buffer_manager();
    
    // Look for a buffer ready to send
    for (int i = 0; i < 2; i++) {
        struct ble_buffer *buf = &mgr->buffers[i];
        if (buf->state == BUFFER_READY) {
            sending_buffer = buf;
            buf->state = BUFFER_SENDING;
            
            // Send buffer contents
            send_buffer_chunked(buf);
            
            // Mark buffer as empty
            reset_buffer(buf);
            sending_buffer = NULL;
            break;
        }
    }
}

/* Initialize BLE scanning */
static int ble_init(void) {
    int err = bt_enable(NULL);
    if (err) {
        LOG_ERR("Bluetooth init failed (err %d)", err);
        return err;
    }

    LOG_INF("Bluetooth initialized");
    return 0;
}

/* Main function */
int main(void) {
    int err;

    LOG_INF("Starting BLE Scanner...");

    // Initialize UART
    err = uart_init();
    if (err) {
        LOG_ERR("UART init failed: %d", err);
        return err;
    }

    // Initialize buffer manager
    err = buffer_manager_init();
    if (err) {
        LOG_ERR("Buffer manager init failed: %d", err);
        return err;
    }

    // Initialize BLE
    err = ble_init();
    if (err) {
        return err;
    }

    // Initialize work items
    k_work_init_delayable(&buffer_switch_work, buffer_switch_handler);
    k_work_init(&uart_send_work, uart_send_handler);

    // Start BLE scanning
    err = bt_le_scan_start(&scan_param, scan_cb);
    if (err) {
        LOG_ERR("Scanning failed to start (err %d)", err);
        return err;
    }

    LOG_INF("Scanning successfully started");

    // Schedule first buffer switch
    k_work_reschedule(&buffer_switch_work, 
                      K_MSEC(SAMPLING_INTERVAL_MS));

    // Main loop
    while (1) {
        k_sleep(K_SECONDS(1));
    }

    return 0;
}