#ifndef BLE_SCANNER_H
#define BLE_SCANNER_H

#include <zephyr/kernel.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/logging/log.h>
#include <zephyr/drivers/uart.h>

/* Configuration Constants */
#define MAX_DEVICES              50    /* Maximum number of devices to track */
#define SAMPLING_INTERVAL_MS     5000  /* Buffer switch interval */
#define UART_BAUD_RATE          115200
#define UART_HEADER_MAGIC       0x55   /* Synchronization pattern: 01010101 */

/* BLE Advertisement Data Structure */
struct __packed device_data {
    uint8_t addr[6];          /* MAC address */
    uint8_t addr_type;        /* Address type (public/random) */
    uint8_t adv_type;         /* Advertisement type */
    int8_t  rssi;            /* RSSI value */
    uint8_t data_len;        /* Length of advertisement data */
    uint8_t data[31];        /* Raw advertisement data */
    uint8_t n_adv;           /* Number of advertisements seen */
    int32_t last_seen;       /* Timestamp of last advertisement */
};

/* Buffer Header Structure */
struct __packed buffer_header {
    uint8_t magic[4];         /* [0x55, 0x55, 0x55, 0x55] */
    uint8_t sequence;         /* Message sequence number */
    uint16_t n_adv_raw;       /* Total advertisements seen */
    uint8_t n_mac;           /* Number of unique MACs */
    int32_t timestamp;       /* Buffer creation timestamp */
};

/* Function Declarations */
int ble_scanner_init(void);
void ble_scanner_start(void);
void ble_scanner_stop(void);

/* Error Codes */
#define ERR_BLE_INIT_FAILED    -1
#define ERR_UART_INIT_FAILED   -2
#define ERR_BUFFER_INIT_FAILED -3

#endif /* BLE_SCANNER_H */