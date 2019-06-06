#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate

./halucinator -c=test/results/STM32469_EVAL/Halt_config.yaml \
    -a=test/results/STM32469_EVAL/UART/Uart_Hyperterminal_DMA--board=STM32469_EVAL--opt=Os--comp=arm-none-eabi-gcc--comp_version=4.9.3_addrs.yaml \
    -m=test/results/STM32469_EVAL/UART/Halt_memory_Uart_Hyperterminal_DMA_Os.yaml --log_blocks -n Halt_UART_DMA