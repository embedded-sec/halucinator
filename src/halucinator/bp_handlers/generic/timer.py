# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a
# non-exclusive license for use of this work by or on behalf of the U.S.
# Government. Export of this data may require a license from the United States
# Government.

import re
from binascii import hexlify
from os import path
import sys
from ..bp_handler import BPHandler, bp_handler
import time
import logging
log = logging.getLogger("Timer")
# log.setLevel(logging.DEBUG)
# sys.path.insert(0,path.dirname(path.dirname(path.abspath(__file__))))


class Timer(BPHandler):
    '''
        Returns an increasing value for each addresss accessed
    '''

    def __init__(self):
        self.start_time = {}
        self.scale = {}

    def register_handler(self, addr, func_name, scale=1):
        '''

        '''
        self.start_time[addr] = time.time()
        self.scale[addr] = scale

        return Timer.get_value

    @bp_handler
    def get_value(self, qemu, addr):
        '''
            Gets the current timer value
        '''
        time_ms = int(
            (time.time() - self.start_time[addr]) * 1000 / float(self.scale[addr]))
        log.info("Time: %i" % time_ms)

        return True, time_ms
