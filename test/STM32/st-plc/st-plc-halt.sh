#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate
./halucinator -c=test/STM32/st-plc/peripheral_config_halt.yaml \
-a=test/STM32/st-plc/st-plc_addrs.yaml \
-m=test/STM32/st-plc/st-plc_memory.yaml --log_blocks -n Halt-ST-PLC -t=5558 -r=5557 -p=2222
