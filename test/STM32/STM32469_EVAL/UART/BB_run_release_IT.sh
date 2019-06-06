#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate

./halucinator -c=test/results/STM32469_EVAL/BB_peripheral_config.yaml \
  -a=test/results/STM32469_EVAL/UART/Uart_Hyperterminal_IT--board\=STM32469_EVAL--opt\=Os--comp\=arm-none-eabi-gcc--comp_version\=4.9.3_addrs.yaml \
  -m=test/results/STM32469_EVAL/UART/Uart_Hyperterminal_IT_Os_memory.yaml --log_blocks -n BB_UART_IT