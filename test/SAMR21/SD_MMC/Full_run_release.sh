#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate
./halucinator -c=test/SAMR21/SD_MMC/Full_SAMR21_config.yaml \
-a=test/SAMR21/SD_MMC/RELEASE_SD_MMC_EXAMPLE21_addrs.yaml \
-m=test/SAMR21/SD_MMC/Memories_Release_SD.yaml --log_blocks -n Full_SD_MMC