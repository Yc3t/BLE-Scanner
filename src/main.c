#include <zephyr/kernel.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/logging/log.h>
#include <zephyr/drivers/uart.h>

LOG_MODULE_REGISTER(ble_scanner, LOG_LEVEL_INF);

#define UART_HEADER_MAGIC      0x55    /* Patrón de sincronización: 01010101 */
#define UART_HEADER_LENGTH     4       /* Longitud de la cabecera */
#define MSG_TYPE_ADV_DATA      0x01 

/* Buffer structures */
struct __packed device_data {
    uint8_t addr[6];          /* MAC Address */
    uint8_t addr_type;        /* Address Type */
    uint8_t adv_type;         /* Advertisement Type */
    int8_t  rssi;            /* RSSI Value */
    uint8_t data_len;        /* Data Length */
    uint8_t data[31];        /* Advertisement Data */
    uint8_t n_adv;           /* Number of advertisements from this MAC */
};

struct __packed buffer_header {
    uint8_t header[UART_HEADER_LENGTH];    /* [0x55, 0x55, 0x55, 0x55] */
    uint8_t sequence;                      /* Numero de secuencia*/
    uint16_t n_adv_raw;                    /* Contador eventos de recepción */
    uint8_t n_mac;                         /* Nº MACs unicas en un buffer */
};

/* Configuración del buffer */
#define MAX_DEVICES 50
#define SAMPLING_INTERVAL_MS 5000  // 5 sec

/*Variables globales buffer*/
static struct device_data device_buffer[MAX_DEVICES];
static struct buffer_header buffer_header;
static bool buffer_active = false;

static const struct device *uart_dev; // Puntero al dispositivo UART

static uint8_t msg_sequence = 0; //Contador de secuencia

/* Ver si añadir o actualizar dispositivo */
static struct device_data *find_or_add_device(const bt_addr_le_t *addr) {
    //Buscar si ya está en el buffer
    for (int i = 0; i < buffer_header.n_mac; i++) {
        //comparar dirección en el buffer con la nueva dirección
        if (memcmp(device_buffer[i].addr, addr->a.val, 6) == 0) {
            return &device_buffer[i];
        }
    }
    
    // Si no se ha encontrado, añadir nuevo dispositivo
    if (buffer_header.n_mac < MAX_DEVICES) {
        //Añadimos un nuevo dispositivo en el device buffer(incrementando la posicion usando n_mac)
        struct device_data *new_device = &device_buffer[buffer_header.n_mac++];
        memcpy(new_device->addr, addr->a.val, 6);
        new_device->n_adv = 0;
        return new_device;
}
    
    return NULL;
}

//Función de escaneo
static void scan_cb(const bt_addr_le_t *addr, int8_t rssi,
                   uint8_t adv_type, struct net_buf_simple *buf)
{
    if (!buffer_active) {
        return;
    }

    buffer_header.n_adv_raw++;

    //cogemos el dispositivo escaneado y vemos si es nuevo o no
    struct device_data *device = find_or_add_device(addr);
    if (device == NULL) {
        return; // Buffer lleno
    }

    // Actualizar los datos del dispositivo
    device->addr_type = addr->type;
    device->adv_type = adv_type;
    device->rssi = rssi;
    device->data_len = MIN(buf->len, sizeof(device->data));
    memcpy(device->data, buf->data, device->data_len);
    device->n_adv++;
}

//Enviar el buffer
static void send_buffer(void) {
    // Header
    const uint8_t *header_data = (const uint8_t *)&buffer_header;
    for (size_t i = 0; i < sizeof(struct buffer_header); i++) {
        uart_poll_out(uart_dev, header_data[i]);
    }

    // Datos
    for (size_t i = 0; i < buffer_header.n_mac; i++) {
        const uint8_t *device_data = (const uint8_t *)&device_buffer[i];
        for (size_t j = 0; j < sizeof(struct device_data); j++) {
            uart_poll_out(uart_dev, device_data[j]);
        }
    }
}

/* Resetear buffer */
static void reset_buffer(void) {
    memset(&buffer_header, 0, sizeof(struct buffer_header));
    memset(device_buffer, 0, sizeof(device_buffer));
    memset(buffer_header.header, UART_HEADER_MAGIC, UART_HEADER_LENGTH);
    buffer_header.sequence = msg_sequence++;
}

/* Timer handler */
static void sampling_timer_handler(struct k_work *work) {
    buffer_active = false;
    
    // Enviar buffer actual 
    send_buffer();
    
    // Resetear buffer para el próximo intervalo
    reset_buffer();
    
    // Restart sampling
    buffer_active = true;
}

//work item para ejecutar el buffer cuando expire el tiempo
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
    .interval   = BT_GAP_SCAN_FAST_INTERVAL,
    .window     = BT_GAP_SCAN_FAST_WINDOW,
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

    // Inicializa buffer
    reset_buffer();
    buffer_active = true;

    // Empezar intervalo de muestreo
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
