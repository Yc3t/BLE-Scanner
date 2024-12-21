#include <zephyr/kernel.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/logging/log.h>
#include <zephyr/drivers/uart.h>

LOG_MODULE_REGISTER(ble_scanner, LOG_LEVEL_INF);

#define UART_HEADER_MAGIC      0x55    /* Patrón de sincronización: 01010101 */
#define UART_HEADER_LENGTH     4       /* Longitud de la cabecera */
#define MSG_TYPE_ADV_DATA      0x01 

/*Estructuras Buffer */
struct __packed device_data {
    uint8_t addr[6];          /* Dirección MAC */
    uint8_t addr_type;        /* Tipo de dirección */
    uint8_t adv_type;         /* Tipo de advertisement */
    int8_t  rssi;            /* Valor RSSI */
    uint8_t data_len;        /* Longitud de datos */
    uint8_t data[31];        /* Datos del advertisement */
    uint8_t n_adv;           /* Número de advertisements de esta MAC */
};

struct __packed buffer_header {
    uint8_t header[UART_HEADER_LENGTH];    /* [0x55, 0x55, 0x55, 0x55] */
    uint8_t sequence;                      /* Número de secuencia */
    uint16_t n_adv_raw;                    /* Contador eventos de recepción */
    uint8_t n_mac;                         /* Nº MACs únicas en buffer */
};

#define MAX_DEVICES 50
#define SAMPLING_INTERVAL_MS 7000  //7 sec

static struct device_data device_buffer[MAX_DEVICES];
static struct buffer_header buffer_header;
static bool buffer_active = false;

/* Definiciones para el protocolo UART */
#define UART_HEADER_MAGIC      0x55    /* Patrón de sincronización: 01010101 */
#define UART_HEADER_LENGTH     4       /* Longitud de la cabecera */
#define MSG_TYPE_ADV_DATA      0x01    /* Tipo mensaje: datos advertisement */

static const struct device *uart_dev; // Puntero al dispositivo UART

static uint8_t msg_sequence = 0; //Contador de secuencia

static struct device_data *find_or_add_device(const bt_addr_le_t *addr) {
    // Buscar dispositivo existente
    for (int i = 0; i < buffer_header.n_mac; i++) {
        if (memcmp(device_buffer[i].addr, addr->a.val, 6) == 0) {
            return &device_buffer[i];
        }
    }
    
    // Verificar límites antes de añadir nuevo dispositivo
    if (buffer_header.n_mac >= 255) {
        LOG_WRN("Buffer lleno: N_MAC = 255");
        return NULL;
    }
    
    if (buffer_header.n_mac < MAX_DEVICES) {
        struct device_data *new_device = &device_buffer[buffer_header.n_mac++];
        memcpy(new_device->addr, addr->a.val, 6);
        new_device->n_adv = 0;
        return new_device;
    }
    
    LOG_WRN("Buffer lleno: MAX_DEVICES alcanzado");
    return NULL;
}

/* Modified scan callback */
static void scan_cb(const bt_addr_le_t *addr, int8_t rssi,
                   uint8_t adv_type, struct net_buf_simple *buf)
{
    if (!buffer_active) {
        return;
    }

    buffer_header.n_adv_raw++;

    struct device_data *device = find_or_add_device(addr);
    if (device == NULL) {
        return; // Buffer is full
    }

    // Update device data
    device->addr_type = addr->type;
    device->adv_type = adv_type;
    device->rssi = rssi;
    device->data_len = MIN(buf->len, sizeof(device->data));
    memcpy(device->data, buf->data, device->data_len);
    device->n_adv++;
}

static void send_buffer(void) {
    // Send header
    const uint8_t *header_data = (const uint8_t *)&buffer_header;
    for (size_t i = 0; i < sizeof(struct buffer_header); i++) {
        uart_poll_out(uart_dev, header_data[i]);
    }

    // Send device data
    for (size_t i = 0; i < buffer_header.n_mac; i++) {
        const uint8_t *device_data = (const uint8_t *)&device_buffer[i];
        for (size_t j = 0; j < sizeof(struct device_data); j++) {
            uart_poll_out(uart_dev, device_data[j]);
        }
    }
}

static void reset_buffer(void) {
    memset(&buffer_header, 0, sizeof(struct buffer_header));
    memset(device_buffer, 0, sizeof(device_buffer));
    memset(buffer_header.header, UART_HEADER_MAGIC, UART_HEADER_LENGTH);
    buffer_header.sequence = msg_sequence++;
    buffer_header.n_mac = 0;     
    buffer_header.n_adv_raw = 0; 
}

/* Timer work handler */
static void sampling_timer_handler(struct k_work *work) {
    buffer_active = false;
    
    // Send current buffer
    send_buffer();
    
    // Reset buffer for next interval
    reset_buffer();
    
    // Restart sampling
    buffer_active = true;
}

K_WORK_DEFINE(sampling_work, sampling_timer_handler);

static void timer_expiry_function(struct k_timer *timer) {
    k_work_submit(&sampling_work);
}

K_TIMER_DEFINE(sampling_timer, timer_expiry_function, NULL);

/* Inicialización del UART */
static int uart_init(void)
{
    // Obtiene UART0 mediate DeviceTree
    uart_dev = DEVICE_DT_GET(DT_NODELABEL(uart0));
    if (!device_is_ready(uart_dev)) {
        LOG_ERR("UART no está listo");
        return -1;
    }
    return 0;
}

/* Parámetros de escaneo BLE */
static struct bt_le_scan_param scan_param = {
    .type       = BT_LE_SCAN_TYPE_PASSIVE,
    .options    = BT_LE_SCAN_OPT_NONE,
    .interval   = BT_GAP_ADV_FAST_INT_MIN_2,  // 0x00a0 (100ms)
    .window     = BT_GAP_ADV_FAST_INT_MIN_2   // 0x00a0 (100ms)
};

int main(void)
{
    int err;

    /* Inicializa UART */
    err = uart_init();
    if (err) {
        LOG_ERR("Falló inicialización UART (err %d)", err);
        return err;
    }

    LOG_INF("Iniciando Escáner BLE con buffer...");

    /* Inicializa Bluetooth */
    err = bt_enable(NULL);
    if (err) {
        LOG_ERR("Falló inicialización Bluetooth (err %d)", err);
        return err;
    }

    // Initialize buffer
    reset_buffer();
    buffer_active = true;

    // Start timer for sampling intervals
    k_timer_start(&sampling_timer, K_MSEC(SAMPLING_INTERVAL_MS), 
                 K_MSEC(SAMPLING_INTERVAL_MS));

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