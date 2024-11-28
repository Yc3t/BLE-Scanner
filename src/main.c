#include <zephyr/kernel.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/logging/log.h>
#include <zephyr/drivers/uart.h>

LOG_MODULE_REGISTER(ble_scanner, LOG_LEVEL_INF);

/* Estructura para almacenar datos de advertisement en bruto */
struct raw_adv_data {
    uint8_t addr[6];          /* Dirección MAC */
    uint8_t addr_type;        /* Tipo de dirección */
    uint8_t adv_type;         /* Tipo de advertisement */
    int8_t  rssi;            /* Valor RSSI */
    uint8_t data_len;        /* Longitud de datos */
    uint8_t data[31];        /* Datos de advertisement */
    uint32_t timestamp;      /* Marca de tiempo */
};

/* Definiciones para el protocolo UART */
#define UART_HEADER_MAGIC      0x55    /* Patrón de sincronización: 01010101 */
#define UART_HEADER_LENGTH     4       /* Longitud de la cabecera */
#define MSG_TYPE_ADV_DATA      0x01    /* Tipo mensaje: datos advertisement */
#define UART_BUFFER_SIZE       256     /* Tamaño del buffer de recepción */

/* Buffer circular para recepción UART */
static uint8_t uart_rx_buf[UART_BUFFER_SIZE];
static uint16_t uart_rx_head = 0;
static uint16_t uart_rx_tail = 0;
static K_MUTEX_DEFINE(uart_mutex);

/* Estructura del mensaje UART */
struct __packed uart_message {
    uint8_t header[UART_HEADER_LENGTH];    /* [0x55, 0x55, 0x55, 0x55] */
    uint8_t type;                          /* Tipo de mensaje */
    uint8_t sequence;                      /* Número de secuencia */
    struct raw_adv_data adv_data;          /* Datos de advertisement */
};

static const struct device *uart_dev;
static uint8_t msg_sequence = 0;

/* Callback de recepción UART */
static void uart_callback(const struct device *dev, void *user_data)
{
    uint8_t c;

    if (!uart_irq_update(dev)) {
        return;
    }

    while (uart_irq_rx_ready(dev)) {
        if (uart_fifo_read(dev, &c, 1) == 1) {
            k_mutex_lock(&uart_mutex, K_FOREVER);
            uart_rx_buf[uart_rx_head] = c;
            uart_rx_head = (uart_rx_head + 1) % UART_BUFFER_SIZE;
            if (uart_rx_head == uart_rx_tail) {
                uart_rx_tail = (uart_rx_tail + 1) % UART_BUFFER_SIZE;
            }
            k_mutex_unlock(&uart_mutex);
        }
    }
}

/* Inicialización UART */
static int uart_init(void)
{
    uart_dev = DEVICE_DT_GET(DT_NODELABEL(uart0));
    if (!device_is_ready(uart_dev)) {
        LOG_ERR("UART no está listo");
        return -1;
    }

    uart_irq_callback_user_data_set(uart_dev, uart_callback, NULL);
    uart_irq_rx_enable(uart_dev);

    return 0;
}

/* Envío de mensaje binario por UART */
static void send_uart_message(const struct raw_adv_data *adv_data)
{
    struct uart_message msg;
    
    memset(msg.header, UART_HEADER_MAGIC, UART_HEADER_LENGTH);
    msg.type = MSG_TYPE_ADV_DATA;
    msg.sequence = msg_sequence++;
    memcpy(&msg.adv_data, adv_data, sizeof(struct raw_adv_data));

    const uint8_t *data = (const uint8_t *)&msg;
    for (size_t i = 0; i < sizeof(struct uart_message); i++) {
        uart_poll_out(uart_dev, data[i]);
    }
}

/* Callback de escaneo BLE */
static void scan_cb(const bt_addr_le_t *addr, int8_t rssi,
                   uint8_t adv_type, struct net_buf_simple *buf)
{
    struct raw_adv_data adv_data;
    
    /* Almacena dirección MAC */
    memcpy(adv_data.addr, addr->a.val, sizeof(adv_data.addr));
    adv_data.addr_type = addr->type;
    
    /* Almacena tipo de advertisement y RSSI */
    adv_data.adv_type = adv_type;
    adv_data.rssi = rssi;
    
    /* Almacena datos de advertisement */
    adv_data.data_len = buf->len > sizeof(adv_data.data) ? 
                        sizeof(adv_data.data) : buf->len;
    memcpy(adv_data.data, buf->data, adv_data.data_len);
    
    /* Almacena marca de tiempo */
    adv_data.timestamp = k_uptime_get_32();

    /* Envía por UART */
    send_uart_message(&adv_data);

    /* Log para debug */
    LOG_INF("BLE ADV - MAC: %02x:%02x:%02x:%02x:%02x:%02x RSSI: %d",
            adv_data.addr[5], adv_data.addr[4], adv_data.addr[3],
            adv_data.addr[2], adv_data.addr[1], adv_data.addr[0],
            rssi);
}

/* Parámetros de escaneo BLE */
static struct bt_le_scan_param scan_param = {
    .type       = BT_LE_SCAN_TYPE_PASSIVE,
    .options    = BT_LE_SCAN_OPT_FILTER_DUPLICATE,
    .interval   = BT_GAP_SCAN_FAST_INTERVAL,
    .window     = BT_GAP_SCAN_FAST_WINDOW,
};

/* Thread para procesamiento UART */
#define UART_STACK_SIZE 1024
#define UART_PRIORITY 7

void uart_process_thread(void *p1, void *p2, void *p3)
{
    while (1) {
        k_mutex_lock(&uart_mutex, K_FOREVER);
        
        while (uart_rx_head != uart_rx_tail) {
            /* Procesa datos recibidos si es necesario */
            uart_rx_tail = (uart_rx_tail + 1) % UART_BUFFER_SIZE;
        }
        
        k_mutex_unlock(&uart_mutex);
        k_sleep(K_MSEC(10));
    }
}

K_THREAD_DEFINE(uart_thread_id, UART_STACK_SIZE,
                uart_process_thread, NULL, NULL, NULL,
                UART_PRIORITY, 0, 0);

int main(void)
{
    int err;

    /* Inicializa UART */
    err = uart_init();
    if (err) {
        LOG_ERR("Falló inicialización UART (err %d)", err);
        return err;
    }

    LOG_INF("Iniciando Escáner BLE...");

    /* Inicializa Bluetooth */
    err = bt_enable(NULL);
    if (err) {
        LOG_ERR("Falló inicialización Bluetooth (err %d)", err);
        return err;
    }

    /* Inicia escaneo */
    err = bt_le_scan_start(&scan_param, scan_cb);
    if (err) {
        LOG_ERR("Falló inicio de escaneo (err %d)", err);
        return err;
    }

    LOG_INF("Escaneo iniciado exitosamente");

    while (1) {
        k_sleep(K_SECONDS(1));
    }

    return 0;
}
