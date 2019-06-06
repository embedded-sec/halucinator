# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC 
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a 
# non-exclusive license for use of this work by or on behalf of the U.S. 
# Government. Export of this data may require a license from the United States 
# Government.

from time import sleep
from ..bp_handler import BPHandler, bp_handler
import struct
import logging
log = logging.getLogger("MbedTimer")
log.setLevel(logging.DEBUG)

class MbedTimer(BPHandler):

    def __init__(self, impl=None):
        pass

    @bp_handler(['wait'])
    def wait(self, qemu, bp_addr):
        log.info("MBed Wait")
        param0 = qemu.regs.r0 # a floating point value
        value = struct.pack("<I",param0)
        stuff = struct.unpack("<f", value)[0]
        sleep(stuff)
        return False, 0#, (param0,)

# TODO: Timer-based callbacks