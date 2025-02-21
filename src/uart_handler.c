#include "uart_handler.h"
#include <zephyr/logging/log.h>
#include "chunk_protocol.h"

LOG_MODULE_REGISTER(uart, LOG_LEVEL_DBG);

static const struct device *uart_dev;
static struct k_sem uart_sem;

/* UART write function */
int uart_write_bytes(const uint8_t *data, size_t len) {
    if (!uart_dev) {
        LOG_ERR("UART device not initialized");
        return -ENODEV;
    }

    LOG_DBG("Writing %d bytes to UART", len);
    for (size_t i = 0; i < len; i++) {
        uart_poll_out(uart_dev, data[i]);  // No return value to check
    }

    return 0;
}

/* UART read function with timeout */
int uart_read_byte(uint8_t *byte, k_timeout_t timeout) {
    if (!uart_dev) {
        LOG_ERR("UART device not initialized");
        return -ENODEV;
    }

    int ret;
    k_timepoint_t end_time = sys_timepoint_calc(timeout);

    do {
        ret = uart_poll_in(uart_dev, byte);
        if (ret == 0) {
            LOG_DBG("Read byte: 0x%02x", *byte);
            return 0;
        }
        if (ret != -EAGAIN) {
            LOG_ERR("UART read error: %d", ret);
            return ret;
        }
        k_sleep(K_MSEC(1));
    } while (sys_timepoint_expired(end_time) == false);

    LOG_DBG("Read timeout");
    return -ETIMEDOUT;
}

/* Initialize UART */
int uart_init(void) {
    int ret;

    // Get UART device
    uart_dev = DEVICE_DT_GET(DT_NODELABEL(uart0));
    if (!device_is_ready(uart_dev)) {
        LOG_ERR("UART device not ready");
        return -ENODEV;
    }

    LOG_INF("UART device %s is ready", uart_dev->name);

    // Initialize semaphore
    k_sem_init(&uart_sem, 1, 1);

    // Configure UART
    const struct uart_config config = {
        .baudrate = UART_BAUD_RATE,
        .parity = UART_CFG_PARITY_NONE,
        .stop_bits = UART_CFG_STOP_BITS_1,
        .data_bits = UART_CFG_DATA_BITS_8,
        .flow_ctrl = UART_CFG_FLOW_CTRL_NONE
    };

    ret = uart_configure(uart_dev, &config);
    if (ret) {
        LOG_ERR("Could not configure UART: %d", ret);
        return ret;
    }

    // Verify configuration
    struct uart_config check_config;
    ret = uart_config_get(uart_dev, &check_config);
    if (ret) {
        LOG_ERR("Could not get UART config: %d", ret);
        return ret;
    }

    if (check_config.baudrate != config.baudrate) {
        LOG_ERR("UART baudrate mismatch: set %d, got %d", 
                config.baudrate, check_config.baudrate);
        return -EINVAL;
    }

    LOG_INF("UART initialized successfully at %d baud", config.baudrate);
    
    // Send a test message
    const uint8_t test[] = "\r\nUART Test\r\n";
    ret = uart_write_bytes(test, sizeof(test) - 1);
    if (ret) {
        LOG_ERR("Failed to send test message: %d", ret);
        return ret;
    }

    return 0;
}

/* Wait for acknowledgment with timeout */
bool uart_wait_ack(uint8_t expected_sequence) {
    uint8_t rx_byte;
    int ret;

    LOG_DBG("Waiting for ACK with sequence %d", expected_sequence);

    // Wait for response
    ret = uart_read_byte(&rx_byte, K_MSEC(ACK_TIMEOUT_MS));
    if (ret == 0) {
        if (rx_byte == CHUNK_TYPE_ACK) {
            LOG_DBG("Received ACK");
            return true;
        } else if (rx_byte == CHUNK_TYPE_NACK) {
            LOG_WRN("Received NACK for sequence %d", expected_sequence);
        } else {
            LOG_WRN("Unexpected response: 0x%02x", rx_byte);
        }
    } else {
        LOG_WRN("Timeout waiting for ACK");
    }

    return false;
}