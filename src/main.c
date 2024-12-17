#include <zephyr/kernel.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/hci.h>
#include <zephyr/logging/log.h>
#include <zephyr/drivers/uart.h>
#include <nrfx_uarte.h>

LOG_MODULE_REGISTER(ble_scanner, LOG_LEVEL_INF);

/* Estructura para almacenar datos de advertisement*/
struct __packed raw_adv_data
{
    uint8_t addr[6];   /* Dirección MAC */
    uint8_t addr_type; /* Tipo de dirección */
    uint8_t adv_type;  /* Tipo de advertisement */
    int8_t rssi;       /* Valor RSSI */
    uint8_t data_len;  /* Longitud de datos */
    uint8_t data[31];  /* Datos de advertisement */
};

struct __packed uart_batch_message
{
    uint8_t header[UART_HEADER_LENGTH] uint8_t type;
    uint8_t sequence
    uint16_t message_count
};

/* Definiciones para la tabla */
#define MAX_MAC_ENTRIES 255
#define MAC_ADDR_LEN 6
#define HASH_TABLE_SIZE 256  // Un índice por cada posible valor del último byte

/* Estructura para una entrada en la tabla */
struct __packed mac_table_entry {
    uint8_t mac[MAC_ADDR_LEN];     // MAC address
    uint8_t n_adv;                 // Número de advertisements
    int8_t last_rssi;             // Último RSSI
    uint8_t addr_type;            // Tipo de dirección
    uint8_t last_adv_type;        // Último tipo de advertisement
};

/* Estructura para el índice de búsqueda rápida */
struct mac_index {
    uint8_t count;                // Número de MACs con este último byte
    uint8_t entries[8];          // Índices a mac_table_entry (máximo 8 por byte)
};

/* Estructura del buffer principal */
struct buffer_control {
    // 1. Tabla principal de datos
    struct mac_table_entry mac_table[MAX_MAC_ENTRIES];
    
    // 2. Índice de búsqueda rápida
    struct mac_index mac_index[HASH_TABLE_SIZE];
    
    // 3. Contadores globales
    uint8_t n_mac;                // Número total de MACs diferentes
    uint16_t n_adv_raw;          // Total de advertisements
    uint64_t interval_start;      // Timestamp del intervalo
} __aligned(4);

/* Definiciones para el protocolo UART */
#define UART_HEADER_MAGIC 0x55 /* Patrón de sincronización: 01010101 */
#define UART_HEADER_LENGTH 4   /* Longitud de la cabecera */
#define MSG_TYPE_ADV_DATA 0x01 /* Tipo mensaje: datos advertisement */

#define MAX_BUFFER_MESSAGES 265
#define RAM_SIZE_KB 256
#define RAM_SIZE_BYTES (RAM_SIZE_KB * 1024)
#define SYSTEM_RESERVED_RAM_KB 64
#define AVAILABLE_RAM_BYTES (RAM_SIZE_BYTES - (SYSTEM_RESERVED_RAM_KB * 1024))

#define RAW_ADV_DATA_SIZE sizeof(struct raw_adv_data)
#define BATCH_HEADER

/* Estructura del mensaje UART */
struct __packed uart_message
{
    uint8_t header[UART_HEADER_LENGTH]; /* [0x55, 0x55, 0x55, 0x55] */
    uint8_t type;                       /* Tipo de mensaje */
    uint8_t sequence;                   /* Número de secuencia */
    struct raw_adv_data adv_data;       /* Datos de advertisement */
};

static const struct device *uart_dev; // Puntero al dispositivo UART

static uint8_t msg_sequence = 0; // Contador de secuencia

/* Función de búsqueda optimizada */
static int8_t find_mac_in_buffer(const uint8_t *mac) {
    uint8_t last_byte = mac[MAC_ADDR_LEN - 1];
    struct mac_index *idx = &adv_buffer.mac_index[last_byte];
    
    // Buscar solo entre las MACs que comparten el último byte
    for (uint8_t i = 0; i < idx->count; i++) {
        uint8_t entry_idx = idx->entries[i];
        if (memcmp(adv_buffer.mac_table[entry_idx].mac, mac, MAC_ADDR_LEN) == 0) {
            return entry_idx;
        }
    }
    return -1;
}

/* Función para añadir nueva MAC */
static int8_t add_new_mac(const uint8_t *mac, uint8_t addr_type, 
                         uint8_t adv_type, int8_t rssi) {
    if (adv_buffer.n_mac >= MAX_MAC_ENTRIES) {
        return -1;  // Buffer lleno
    }

    uint8_t last_byte = mac[MAC_ADDR_LEN - 1];
    struct mac_index *idx = &adv_buffer.mac_index[last_byte];
    
    if (idx->count >= 8) {
        return -1;  // Demasiadas MACs con el mismo último byte
    }

    // Añadir nueva entrada
    uint8_t new_idx = adv_buffer.n_mac;
    struct mac_table_entry *new_entry = &adv_buffer.mac_table[new_idx];
    
    memcpy(new_entry->mac, mac, MAC_ADDR_LEN);
    new_entry->n_adv = 1;
    new_entry->last_rssi = rssi;
    new_entry->addr_type = addr_type;
    new_entry->last_adv_type = adv_type;

    // Actualizar índice
    idx->entries[idx->count++] = new_idx;
    adv_buffer.n_mac++;

    return new_idx;
}

static struct buffer_control adv_buffer = {0};
static void send_buffer()
{
    if (adv_buffer.count == 0){
        return;
    }
    // send the header

    struct uart_batch_message batch_header = {
        .type = ??
        .sequence = msg_sequence++
        .message_count = adv_buffer.count
    }

   //treat the struct as a series of bytes(common in uart) 
    const uint8_t *header_data = (const uint8 *)&batch_header


    memset(batch_header.header, UART_HEADER_MAGIC, UART_HEADER_LENGTH); //??

    //send the header data 
    for (size_t i = 0; i < sizeof(struct uart_batch_message); i++)
    {
        uart_poll_out(uart_dev,header_data[i])
    }

    //send the buffer messages

    for (size_t i=0; i<adv_buffer.count; i++){
        //...
        uart_poll_out(uart_dev,msg_data[?])

    }






    //send the messageses


    

    uart_poll_out()
}

/* Inicialización del UART */
static int uart_init(void)
{
    // Obtiene UART0 mediate DeviceTree
    uart_dev = DEVICE_DT_GET(DT_NODELABEL(uart0));
    if (!device_is_ready(uart_dev))
    {
        LOG_ERR("UART no está listo");
        return -1;
    }
    return 0;
}

/* Callback de escaneo BLE*/
static void scan_cb(const bt_addr_le_t *addr, int8_t rssi,
                    uint8_t adv_type, struct net_buf_simple *buf)
{
    /* Almacena los datos del advertisement */
    struct raw_adv_data adv_data = {0};

    memcpy(adv_data.addr, addr->a.val, sizeof(adv_data.addr)); // Dirección MAC
    adv_data.addr_type = addr->type;                           // Tipo de dirección
    adv_data.adv_type = adv_type;                              // Tipo Advertisiement
    adv_data.rssi = rssi;                                      // RSSI

    /* Calcula y limita la longitud de los datos*/
    adv_data.data_len = MIN(buf->len, sizeof(adv_data.data));
    /* Copia los datos del advertisement */
    memcpy(adv_data.data, buf->data, adv_data.data_len);
    /* Envía a través del UART */
    send_uart_message(&adv_data);
}

/* Parámetros de escaneo BLE */
static struct bt_le_scan_param scan_param = {
    // Configuración 1: Rápida
    .type = BT_LE_SCAN_TYPE_PASSIVE,
    .options = BT_LE_SCAN_OPT_NONE, // Sin filtro de duplicados
    .interval = BT_GAP_SCAN_FAST_INTERVAL,
    .window = BT_GAP_SCAN_FAST_WINDOW,
};

int main(void)
{
    int err;

    /* Inicializa UART */
    err = uart_init();
    if (err)
    {
        LOG_ERR("Falló inicialización UART (err %d)", err);
        return err;
    }

    LOG_INF("Iniciando Escáner BLE...");

    /* Inicializa Bluetooth */
    err = bt_enable(NULL);
    if (err)
    {
        LOG_ERR("Falló inicialización Bluetooth (err %d)", err);
        return err;
    }

    /* Inicia escaneo */
    err = bt_le_scan_start(&scan_param, scan_cb);
    if (err)
    {
        LOG_ERR("Falló inicio de escaneo (err %d)", err);
        return err;
    }

    LOG_INF("Escaneo iniciado exitosamente");

    while (1)
    {
        k_sleep(K_SECONDS(1));
    }

    return 0;
}
