#! /bin/bash

source ~/.virtualenvs/halucinator/bin/activate
./halucinator -c=test/SAMR21/SD_MMC/SAMR21_config_no_intercepts.yaml \
-a=test/SAMR21/SD_MMC/RELEASE_SD_MMC_EXAMPLE21_addrs.yaml \
-m=test/SAMR21/SD_MMC/Memories_Release_SD.yaml --log_blocks -n SD_MMC_release_no_intercepts