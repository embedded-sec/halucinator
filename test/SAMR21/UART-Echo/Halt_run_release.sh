#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate
./halucinator  -c=test/SAMR21/UART-Echo/Halt_SAMR21_config.yaml \
               -m=test/SAMR21/UART-Echo/Halt_Memories_Release_USART.yaml \
               -a=test/SAMR21/UART-Echo/Release_USART_QUICK_START1_addrs.yaml \
               --log_blocks -n Halt_UART-Echo