#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate
./halucinator -c=test/SAMR21/Wireless/SAMR21_config.yaml \
-a=test/SAMR21/Wireless/DEBUG_UART_EXAMPLES_UDP-UNICAST-RECEIVER2_addrs.yaml \
-m=test/SAMR21/Wireless/Memories_Debug_Receive.yaml --log_blocks -n UDP_Receive