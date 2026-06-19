cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(nucleo_l476rg_bug_wrong_boot_text)

target_sources(app PRIVATE src/main.c)
