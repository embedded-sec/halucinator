Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains certain rights in this software.

from ..bp_handler import BPHandler, bp_handler
import logging
import time
log = logging.getLogger("Contiki")
# log.setLevel(logging.DEBUG)


class Contiki(BPHandler):

    def __init__(self, model=None):
        BPHandler.__init__(self)
        self.model = model
        self.start_time = time.time()
        self.ticks_per_second = 128

    def register_handler(self, addr, func_name, ticks_per_second=None):
        if ticks_per_second is not None:
            self.ticks_per_second = ticks_per_second
        return BPHandler.register_handler(self, addr, func_name)

    @bp_handler(['clock_time'])
    def clock_time(self, qemu, bp_addr):
        ticks = time.time() - self.start_time
        ticks = int(ticks * self.ticks_per_second)
        log.debug("#Ticks: %i" % ticks)
        return True, ticks

    @bp_handler(['clock_seconds'])
    def clock_seconds(self, qemu, bp_addr):
        secs = int(time.time() - self.start_time)
        log.debug("#Seconds: %i" % secs)
        return True, secs
