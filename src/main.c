#include "uart_handler.h"
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(main, LOG_LEVEL_INF);

/* Test message to send */
static const uint8_t test_msg[] = "UART Test Message\r\n";

/* Work item for periodic sending */
static struct k_work_delayable send_work;

/* Send work handler */
static void send_work_handler(struct k_work *work) {
    // Send test message
    int err = uart_write_bytes(test_msg, sizeof(test_msg) - 1);
    if (err) {
        LOG_ERR("Failed to send test message: %d", err);
    } else {
        LOG_INF("Sent test message");
    }

    // Try to read any response (non-blocking)
    uint8_t byte;
    while (uart_read_byte(&byte, K_NO_WAIT) == 0) {
        LOG_INF("Received byte: 0x%02X", byte);
    }

    // Schedule next send
    k_work_reschedule(&send_work, K_MSEC(1000));
}

/* Main function */
int main(void) {
    int err;

    LOG_INF("Starting UART Test...");

    // Initialize UART
    err = uart_init();
    if (err) {
        LOG_ERR("UART init failed: %d", err);
        return err;
    }

    LOG_INF("UART initialized successfully");

    // Initialize work item
    k_work_init_delayable(&send_work, send_work_handler);

    // Schedule first send
    k_work_reschedule(&send_work, K_MSEC(1000));

    // Main loop
    while (1) {
        k_sleep(K_SECONDS(1));
    }

    return 0;
}