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

# sys.path.insert(0,path.dirname(path.dirname(path.abspath(__file__))))


class Counter(BPHandler):
    '''
        Returns an increasing value for each addresss accessed
    '''

    def __init__(self):
        self.increment = {}
        self.counts = {}

    def register_handler(self, addr, func_name, increment=1):
        '''

        '''
        self.increment[addr] = increment
        self.counts[addr] = 0

        return Counter.get_value

    @bp_handler
    def get_value(self, qemu, addr):
        '''
            Gets the counter value
        '''
        self.counts[addr] += self.increment[addr]
        return True, self.counts[addr]
