#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate
./halucinator -c=test/SAMR21/Wireless/SAMR21_config_RF233.yaml \
-a=test/SAMR21/Wireless/DEBUG_UART_EXAMPLES_UDP-UNICAST-RECEIVER2_addrs.yaml \
-m=test/SAMR21/Wireless/Memories_Debug_Receive.yaml --log_blocks=in_asm -n UDP_Received_rf233 \
-t=5558 -r=5557 -p=2222