#!/bin/bash
# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. 
# Government retains certain rights in this software.



arm-none-eabi-objcopy -O binary ${1} ${1}.bin