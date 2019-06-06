#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate
./halucinator -c=test/SAMR21/HTTP/SAMR21_config_HLE.yaml \
-a=test/SAMR21/HTTP/DEBUG_THIRDPARTY_LWIP_RAW_BASIC_HTTP_EXAMPLE_AJAX1_addrs.yaml \
-m=test/SAMR21/HTTP/Memories_Debug_USART.yaml --log_blocks -n HTTP_Debug