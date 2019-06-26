# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. 
# Government retains certain rights in this software.

from ..bp_handler import BPHandler, bp_handler
import logging
log = logging.getLogger("MbedBoot")
log.setLevel(logging.DEBUG)

class MbedBoot(BPHandler):

    def __init__(self, impl=None):
        BPHandler.__init__(self)

    @bp_handler(['SystemInit'])
    def SystemInit(self, qemu, bp_addr):
        log.info("MBED System")
        log.info("LR: %s" % hex(qemu.regs.lr))
        # Do nothing, at all
        return True, None

    @bp_handler(['mbed_sdk_init'])
    def mbed_sdk_init(self, qemu, bp_addr):
        log.info("mbed_sdk_init")
        # ...you don't need to do that
        return True, None

    @bp_handler(['software_init_hook'])
    def software_init_hook(self, qemu, bp_addr):
        log.info("software_init_hook")
        # Nope.
        return True, 0

    @bp_handler(['software_init_hook_rtos'])
    def software_init_hook_rtos(self, qemu, bp_addr):
        log.info("software_init_hook_rtos")
        # Not even once
        return True, 0


