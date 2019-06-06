#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate
./halucinator -c=test/SAMR21/SD_MMC/SAMR21_config.yaml \
-a=test/SAMR21/SD_MMC/DEBUG_SD_MMC_EXAMPLE21_addrs.yaml \
-m=test/SAMR21/SD_MMC/Memories_Debug_SD.yaml --log_blocks -n SD_MMC