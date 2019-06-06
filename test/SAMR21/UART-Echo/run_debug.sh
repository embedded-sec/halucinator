#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate
./halucinator  -c=test/SAMR21/UART-Echo/SAMR21_config.yaml \
               -m=test/SAMR21/UART-Echo/Memories_Debug_USART.yaml \
               -a=test/SAMR21/UART-Echo/Debug_USART_QUICK_START1_addrs.yaml \
               --log_blocks -n UART-Echo_debug