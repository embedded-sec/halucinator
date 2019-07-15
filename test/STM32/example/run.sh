#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate

./halucinator -c=test/STM32/example/Uart_Hyperterminal_IT_O0_config.yaml \
  -a=test/STM32/example/Uart_Hyperterminal_IT_O0_addrs.yaml \
  -m=test/STM32/example/Uart_Hyperterminal_IT_O0_memory.yaml --log_blocks -n Uart_Example