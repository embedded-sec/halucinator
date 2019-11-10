Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains certain rights in this software.

from ...peripheral_models.interrupts import Interrupts
from avatar2.peripherals.avatar_peripheral import AvatarPeripheral
from ..intercepts import tx_map, rx_map
from ..bp_handler import BPHandler, bp_handler
import logging
log = logging.getLogger("EXT_Int")
log.setLevel(logging.DEBUG)


class EXT_Int(BPHandler, AvatarPeripheral):

    def __init__(self, impl=Interrupts):
        self.callbacks = {}
        self.model = impl
        self.org_lr = None
        self.current_channel = 0
        self.name = 'Atmel_EIC'
        self.address = 0x40001800
        self.size = 2048

        log.info("Setting Handlers")
        AvatarPeripheral.__init__(self, self.name, self.address, self.size)

        self.read_handler[0:self.size] = self.hw_read
        self.write_handler[0:self.size] = self.hw_write

    def get_mmio_info(self):
        return self.name, self.address, self.size, 'rw-'

    def hw_read(self, offset, size, pc):
        value = 0
        if offset == 0x10:  # Set interrupt
            for channel, isr_name in list(self.channel_map.items()):

                if self.model.is_active(isr_name):
                    value |= (1 << channel)
        log.info("Read from addr, 0x%08x size: %i value: 0x%0x, pc:%s" %
                 (self.address + offset, size, value, hex(pc)))
        return value

    def hw_write(self, offset, size, value, pc):
        log.info("Write to addr, 0x%08x size: %i value: 0x%0x pc:%s" %
                 (self.address + offset, size, value, hex(pc)))
        if offset == 8:  # Clear interrupt
            for channel, isr_name in list(self.channel_map.items()):
                if self.model.is_active(isr_name):
                    log.info("Clearing %i:%s" % (channel, isr_name))
                    self.model.clear_active(isr_name)
        return True

    def register_handler(self, addr, func_name, channel_map=None):
        # Can be called for each function registered with the class
        if channel_map is not None:
            log.info("Setting Channel map: %s" % str(channel_map))
            self.channel_map = channel_map
        return BPHandler.register_handler(self, addr, func_name)

    # @bp_handler(['EIC_Handler'])
    # def EIC_Handler(self, qemu, bp_addr):
    #     log.info("In EIC_Handler: %s" % hex(bp_addr))
    #     return False, None

    @bp_handler(['extint_register_callback'])
    def register_callback(self, qemu, bp_addr):
        log.info("Callback Set %s" % hex(qemu.regs.r0))
        return False, None  # Just let it run,

    # @bp_handler("dummy")
    # def dummy(self, qemu, bp_addr):

    #     return True, None
