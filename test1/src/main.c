#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include "myfunction.h"

int main(void)
{
  int a = 3, b=4;

  while (1){
    printk("The sum of %d and %d is %d\n", a,b, sum(a,b));
    k_msleep(1000);
  }
}
