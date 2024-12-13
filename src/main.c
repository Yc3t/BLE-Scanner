#include <zephyr/kernel.h>
#include <zephyr/drivers/uart.h>
#include <nrfx_uarte.h>
#include <zephyr/sys/printk.h>

#define UARTE_NODE DT_NODELABEL(uart0)
static nrfx_uarte_t uarte = NRFX_UARTE_INSTANCE(0);
static volatile bool transfer_completed = false;

static void uarte_handler(const nrfx_uarte_event_t *p_event, void *p_context)
{
    if (p_event->type == NRFX_UARTE_EVT_TX_DONE) {
        transfer_completed = true;
    }
}

int main(void)
{
    nrfx_err_t err;
    uint8_t counter = 0;
    
    // Configure UARTE
    nrfx_uarte_config_t uarte_config = NRFX_UARTE_DEFAULT_CONFIG(
        DT_PROP(UARTE_NODE, tx_pin),
        DT_PROP(UARTE_NODE, rx_pin));
    uarte_config.baudrate = NRF_UARTE_BAUDRATE_115200;
    uarte_config.skip_gpio_cfg = false;
    uarte_config.skip_psel_cfg = false;

    // Initialize UARTE
    err = nrfx_uarte_init(&uarte, &uarte_config, uarte_handler);
    if (err != NRFX_SUCCESS) {
        printk("UARTE init failed: %x\n", err);
        return -1;
    }

    while (1) {
        char buffer[16];
        int len = snprintf(buffer, sizeof(buffer), "Count: %d\n", counter++);
        
        transfer_completed = false;
        err = nrfx_uarte_tx(&uarte, (uint8_t *)buffer, len, 0);
        if (err != NRFX_SUCCESS) {
            printk("UARTE TX failed: %x\n", err);
            continue;
        }

        // Wait for transfer to complete
        while (!transfer_completed) {
            k_sleep(K_MSEC(1));
        }

        // Wait 1 second before sending next number
        k_sleep(K_SECONDS(1));
    }
    return 0;
}
