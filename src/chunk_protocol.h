#ifndef CHUNK_PROTOCOL_H
#define CHUNK_PROTOCOL_H

#include "buffer_manager.h"

#define CHUNK_SIZE      128
#define MAX_RETRIES     3
#define ACK_TIMEOUT_MS  1000


//maximum devices per chunk

#define CHUNK_HEADER_SIZE   8
#define CHUNK_CRC_SIZE      2
#define CHUNK_PAYLOAD_SIZE (CHUNK_SIZE - CHUNK_HEADER_SIZE - CHUNK_CRC_SIZE)
#define MAX_DEVICES_PER_CHUNK (CHUNK_PAYLOAD_SIZE / sizeof(struct device_data))

enum chunk_type {
    CHUNK_TYPE_START = 0X01,
    CHUNK_TYPE_DATA = 0X02,
    CHUNK_TYPE_END = 0X03,
    CHUNK_TYPE_ACK = 0X04,
    CHUNK_TYPE_NACK = 0x05
}

// chunk header structure

struct __packed chunk{
    struct chunk_header header;
    struct device_data devices[MAX_DEVICES_PER_CHUNK]
    uint16_t crc;
}

void send_buffer_chunked(struct ble_buffer *buffer);
uint16_t calculate_crc16(const uint8_t *data,size_t length);

#endif