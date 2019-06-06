#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate

./halucinator -c=test/results/STM32469_EVAL/Halt_config.yaml \
-a=test/results/STM32469_EVAL/Fatfs_uSD/FatFS_uSD--board=STM32469_EVAL--opt=Os--comp=arm-none-eabi-gcc--comp_version=4.9.3_addrs.yaml \
-m=test/results/STM32469_EVAL/Fatfs_uSD/Halt_memory_FatFS_uSD_Os.yaml --log_blocks -n Halt_FatFS