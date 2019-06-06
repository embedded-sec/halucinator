#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate
./halucinator -c=test/SAMR21/Wireless/BB_SAMR21_config_RF233.yaml \
-a=test/SAMR21/Wireless/Release_EXAMPLES_UDP-UNICAST-RECEIVER_addrs.yaml \
-m=test/SAMR21/Wireless/Memories_Release_Receive.yaml --log_blocks=in_asm -n BB_UDP_Received_Release_rf233 \
-t=5558 -r=5557 -p=2222