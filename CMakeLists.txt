cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})

project(scan-adv-2)

target_sources(app PRIVATE
    src/main.c
    src/buffer_manager.c
    src/uart_handler.c
    src/chunk_protocol.c
)
