#include "uart_handler.h"
#include "chunk_protocol.h"

LOG_MODULE_DECLARE(ble_scanner);

static const struct device *uart_dev;
static struct k_sem uart_sem;

/* UART write function */
int uart_write_bytes(const uint8_t *data, size_t len) {
    if (!uart_dev) {
        return -ENODEV;
    }

    for (size_t i = 0; i < len; i++) {
        uart_poll_out(uart_dev, data[i]);
    }

    return 0;
}

/* UART read function with timeout */
static int uart_read_byte(uint8_t *byte, k_timeout_t timeout) {
    if (!uart_dev) {
        return -ENODEV;
    }

    int ret;
    k_timepoint_t end_time = sys_timepoint_calc(timeout);

    do {
        ret = uart_poll_in(uart_dev, byte);
        if (ret == 0) {
            return 0;
        }
        k_sleep(K_MSEC(1));
    } while (sys_timepoint_expired(end_time) == false);

    return -ETIMEDOUT;
}

/* Wait for acknowledgment with timeout */
bool uart_wait_ack(uint8_t expected_sequence) {
    uint8_t rx_byte;
    int ret;

    // Wait for response
    ret = uart_read_byte(&rx_byte, K_MSEC(ACK_TIMEOUT_MS));
    if (ret == 0) {
        if (rx_byte == CHUNK_TYPE_ACK) {
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

/* Initialize UART */
int uart_init(void) {
    // Get UART device
    uart_dev = DEVICE_DT_GET(DT_NODELABEL(uart0));
    if (!device_is_ready(uart_dev)) {
        LOG_ERR("UART device not ready");
        return -ENODEV;
    }

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

    int ret = uart_configure(uart_dev, &config);
    if (ret) {
        LOG_ERR("Could not configure UART: %d", ret);
        return ret;
    }

    LOG_INF("UART initialized successfully");
    return 0;
}