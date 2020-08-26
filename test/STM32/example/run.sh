#! /bin/bash

#source ~/.virtualenvs/halucinator/bin/activate

halucinator -c=test/STM32/example/Uart_Hyperterminal_IT_O0_config.yaml \
  -c test/STM32/example/Uart_Hyperterminal_IT_O0_addrs.yaml \
  -c test/STM32/example/Uart_Hyperterminal_IT_O0_memory.yaml --log_blocks=trace-nochain -n Uart_Example
