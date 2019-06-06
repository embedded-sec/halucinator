#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate
./halucinator  -c=test/SAMR21/UART-Echo/Halt_SAMR21_config.yaml \
               -a=test/SAMR21/SD_MMC/RELEASE_SD_MMC_EXAMPLE21_addrs.yaml \
               -m=test/SAMR21/SD_MMC/Halt_Memories_Release_SD.yaml \
               --log_blocks -n Halt_SD_MMC