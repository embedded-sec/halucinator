# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a
# non-exclusive license for use of this work by or on behalf of the U.S.
# Government. Export of this data may require a license from the United States
# Government.


from ...peripheral_models.ieee802_15_4 import IEEE802_15_4
from ..intercepts import tx_map, rx_map
from ..bp_handler import BPHandler, bp_handler
from collections import defaultdict, deque
import struct
import binascii
import os
import logging
import time
log = logging.getLogger("RF233")
log.setLevel(logging.DEBUG)

# SPI Addresses
RF233_REG_IRQ_STATUS = 0x0F
RF233_REG_TRX_STATE = 0x02
RF233_REG_TRX_STATUS = 0x01
IRQ_TRX_END = 1 << 3

# Intercepts base on functions in rf233.c


class RF233Radio(BPHandler):
    def __init__(self, model=IEEE802_15_4):
        BPHandler.__init__(self)
        self.model = model
        self.regs = defaultdict(int)
        self.model.rx_frame_isr = 20
        self.last_rx_time = time.time()
        self.buffered_frame = 0

    def get_id(self, qemu):
        return 'SAMR21Radio'

    @bp_handler(['rf233_send', 'trx_frame_write'])
    def send(self, qemu, bp_addr):
        # int rf233_send(const void *data, unsigned short len);
        log.debug("Send")
        frame = qemu.read_memory(
            qemu.regs.r0, 1, qemu.regs.r1 & 0xFF, raw=True)
        self.model.tx_frame(self.get_id(qemu), frame)
        # import os; os.system("stty sane")
        # import IPython; IPython.embed()
        return True, 0

    @bp_handler(['trx_frame_read'])
    def read_len(self, qemu, bp_addr):
        # Actually just gets the length of the frame
        # int rf233_read(void *buf, unsigned short bufsize);
        log.debug("trx_frame_read")
        if self.model.has_frame() is not None:

            num_frames, frame_len = self.model.get_frame_info()
            log.debug("%s: Frame Len %i" % (qemu.regs.r0, frame_len))
            qemu.write_memory(qemu.regs.r0, 1, frame_len + 2, 1)
        else:
            qemu.write_memory(qemu.regs.r0, 1, 0, 1)

        return True, None

    @bp_handler(['trx_sram_read'])
    def sram_read(self, qemu, bp_addr):
        log.debug("Sram Read Called")
        if self.model.has_frame() is not None:
            frame = self.model.get_first_frame()
            buf_addr = qemu.regs.r1
            buf_size = qemu.regs.r2
            if len(frame) <= buf_size:
                log.debug("Writing Buffer to memory %s " %
                          (binascii.hexlify(frame)))
                qemu.write_memory(buf_addr, 1, frame, len(frame), raw=True)
        return True, None

    @bp_handler(['rf233_on'])
    def on(self, qemu, bp_addr):
        # int rf233_on(void);
        log.debug("rf233_on")
        self.model.rx_isr_enabled = True
        return True, 0

    @bp_handler(['rf_get_channel'])  # used
    def get_channel(self, qemu, bp_addr):
        # int rf_get_channel(void);
        log.debug("rf_get_channel")
        return True, 0

    @bp_handler(['rf_set_channel'])  # used
    def set_channel(self, qemu, bp_addr):
        # int rf_set_channel(uint8_t ch);
        log.debug("rf_set_channel")
        return True, 0

    @bp_handler(['SetIEEEAddr'])
    def SetIEEEAddr(self, qemu, bp_addr):
        # void SetIEEEAddr(uint8_t *ieee_addr);
        addr = qemu.regs.r0
        # TODO Check endian of address
        self.model.IEEEAddr = qemu.read_memory(addr, 1, 8, raw=True)
        log.debug("SetIEEEAddr")
        return True, None

    @bp_handler(['trx_reg_read'])  # used
    def trx_reg_read(self, qemu, bp_addr):
        reg = qemu.regs.r0
        log.debug("trx_reg_read")
        if reg == RF233_REG_IRQ_STATUS:
            ret_val = 0
            if self.model.has_frame():
                ret_val = IRQ_TRX_END
            return True, ret_val
        elif reg == RF233_REG_TRX_STATUS:
            ret_val = self.regs[RF233_REG_TRX_STATE]
        elif reg in self.regs:
            ret_val = self.regs[reg]
        else:
            log.debug("trx_reg_read: %s Unimplemented register returning  0, %s" % (
                reg, hex(qemu.regs.lr)))
            ret_val = 0
        return True, ret_val

    @bp_handler(['trx_spi_init'])  # used
    def trx_spi_init(self, qemu, bp_addr):
        # Sets up the EXTI callback
        log.debug("trx_spi_init")
        # Set Thumb bit
        qemu.regs.r0 = qemu.avatar.callables['AT86RFX_ISR'] | 1
        qemu.regs.r1 = 0
        qemu.regs.r2 = 0
        # Set Thumb bit
        qemu.regs.pc = qemu.avatar.callables['extint_register_callback'] | 1
        return False, None

    @bp_handler(['trx_reg_write'])  # used
    def trx_reg_write(self, qemu, bp_addr):
        self.regs[qemu.regs.r0] = qemu.regs.r1
        log.debug("trx_reg_write")
        return True, None
