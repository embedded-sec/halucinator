#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate
./halucinator -c=test/SAMR21/Wireless/SAMR21_config.yaml \
-a=test/SAMR21/Wireless/DEBUG_UART_EXAMPLES_UDP-UNICAST-SENDER1_addrs.yaml \
-m=test/SAMR21/Wireless/Memories_Debug_Send.yaml --log_blocks -n UDP_Send