#ifndef BLE_SCANNER_H
#define BLE_SCANNER_H

#include <zephyr/kernel.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/logging/log.h>
#include <zephyr/drivers/uart.h>


//configuration constants

#define MAX_DEVICES             50      //max devices to track
#define SAMPLING_INTERVAL_MS    5000    //buffer switch interval
#define UART_BAUD_RATE          115200
#define UART_HEADER_MAGIC       0x55   //sync pattern 01010101


//ble data struct

struct __packed device_data{
    uint8_t addr[6];
    uint8_t addr_type;
    uint8_t adv_type;
    int8_t rssi;
    uint8_t data_len;
    uint8_t data[31];
    uint8_t n_adv;
    int32_t last_seen;
}


//header structure

struct __packed buffer_header{
    uint8_t magic[4];
    uint8_t sequence;
    uint16_t n_adv_raw_;
    uint8_t n_mac;
    int32_t timestamp;
}

//functions we need
int ble_scanner_init(void);
void ble_scanner_start(void);
void ble_scanner_stop(void);


//error codes

#define ERR_BLE_INIT_FAILED -1
#define ERR_UART_INIT_FAILED -2
#define ERR_BUFFER_INIT_FAILED -3

#endif
