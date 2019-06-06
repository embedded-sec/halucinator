#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate
./halucinator -c=test/SAMR21/HTTP/Full_SAMR21_config_LWIP.yaml \
-a=test/SAMR21/HTTP/RELEASE_THIRDPARTY_LWIP_RAW_BASIC_HTTP_EXAMPLE_AJAX1_addrs.yaml \
-m=test/SAMR21/HTTP/Memories_Release_USART.yaml --log_blocks -n Full_HTTP_Release_LWIP