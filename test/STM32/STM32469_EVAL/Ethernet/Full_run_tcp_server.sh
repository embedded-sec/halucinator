#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate
./halucinator -c=test/STM32/STM32469_EVAL/Full_peripheral_config.yaml \
-a=test/STM32/STM32469_EVAL/Ethernet/TCP_Echo_Server--board=STM32469I_Eval--opt=Os--comp=arm-none-eabi-gcc--comp_version=4.9.3_addrs.yaml \
-m=test/STM32/STM32469_EVAL/Ethernet/TCP_Echo_Server_Os_memory.yaml --log_blocks -n Full_TCP_Echo_Server -t=5558 -r=5557 -p=2222