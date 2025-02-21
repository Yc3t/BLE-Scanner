#ifndef UART_HANDLER_H
#define UART_HANDLER_H

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/logging/log.h>
#include "chunk_protocol.h"  /* For CHUNK_TYPE_* constants */

/* Constants */
#define UART_BAUD_RATE    115200
#define ACK_TIMEOUT_MS    100

/* Function declarations */
int uart_init(void);
int uart_write_bytes(const uint8_t *data, size_t len);
int uart_read_byte(uint8_t *byte, k_timeout_t timeout);
bool uart_wait_ack(uint8_t expected_sequence);

#endif /* UART_HANDLER_H */