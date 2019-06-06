#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate
./halucinator -c=test/SAMR21/Wireless/BB_SAMR21_config_RF233.yaml \
-a=test/SAMR21/Wireless/Release_EXAMPLES_UDP-UNICAST-SENDER_addrs.yaml \
-m=test/SAMR21/Wireless/Memories_Release_Send_RF233.yaml --log_blocks=in_asm -n BB_UDP_Send_Release_RF233