#ifndef CHUNK_PROTOCOL_H
#define CHUNK_PROTOCOL_H

#include "buffer_manager.h"

/* Chunk Configuration */
#define CHUNK_SIZE              128   /* Maximum chunk size */
#define MAX_RETRIES            3     /* Maximum transmission retries */
#define ACK_TIMEOUT_MS         100   /* Acknowledgment timeout */

/* Calculate maximum devices per chunk */
#define CHUNK_HEADER_SIZE      8
#define CHUNK_CRC_SIZE        2
#define CHUNK_PAYLOAD_SIZE    (CHUNK_SIZE - CHUNK_HEADER_SIZE - CHUNK_CRC_SIZE)
#define MAX_DEVICES_PER_CHUNK (CHUNK_PAYLOAD_SIZE / sizeof(struct device_data))

/* Chunk Types */
enum chunk_type {
    CHUNK_TYPE_START = 0x01,
    CHUNK_TYPE_DATA  = 0x02,
    CHUNK_TYPE_END   = 0x03,
    CHUNK_TYPE_ACK   = 0x04,
    CHUNK_TYPE_NACK  = 0x05
};

/* Chunk Header Structure */
struct __packed chunk_header {
    uint8_t start_marker;      /* Always 0x55 */
    uint8_t type;             /* Chunk type */
    uint8_t sequence;         /* Sequence number */
    uint8_t n_devices;        /* Number of devices in chunk */
    uint16_t total_devices;   /* Total devices in message */
    uint16_t chunk_offset;    /* Chunk number */
};

/* Complete Chunk Structure */
struct __packed chunk {
    struct chunk_header header;
    struct device_data devices[MAX_DEVICES_PER_CHUNK];
    uint16_t crc;
};

/* Function Declarations */
void send_buffer_chunked(struct ble_buffer *buffer);
uint16_t calculate_crc16(const uint8_t *data, size_t length);

#endif /* CHUNK_PROTOCOL_H */