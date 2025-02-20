#ifndef UART_HANDLER_H
#define UART_HANDLER_H

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/logging/log.h>
#include "chunk_protocol.h"  /* For ACK_TIMEOUT_MS */

/* Constants */
#define UART_BAUD_RATE    115200

/* Function declarations */
int uart_init(void);
int uart_write_bytes(const uint8_t *data, size_t len);
bool uart_wait_ack(uint8_t expected_sequence);

#endif /* UART_HANDLER_H */ 