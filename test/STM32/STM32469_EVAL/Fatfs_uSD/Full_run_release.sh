#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate

./halucinator -c=test/results/STM32469_EVAL/Full_peripheral_config.yaml \
-a=test/results/STM32469_EVAL/Fatfs_uSD/FatFS_uSD--board=STM32469_EVAL--opt=Os--comp=arm-none-eabi-gcc--comp_version=4.9.3_addrs.yaml \
-m=test/results/STM32469_EVAL/Fatfs_uSD/FatFS_uSD_Os_memory.yaml --log_blocks -n Full_FatFS_uSD