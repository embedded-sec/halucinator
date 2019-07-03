# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a
# non-exclusive license for use of this work by or on behalf of the U.S.
# Government. Export of this data may require a license from the United States
# Government.


from ...peripheral_models.ethernet import EthernetModel
from ..intercepts import tx_map, rx_map
from ..bp_handler import BPHandler, bp_handler
from collections import defaultdict, deque
import struct
import binascii
import os
import logging
import time
log = logging.getLogger("Ksz8851Eth")
log.setLevel(logging.INFO)

# SPI Addresses
REG_RX_FHR_BYTE_CNT = 0x7E
REG_RX_FHR_STATUS = 0x7C
REG_TX_MEM_INFO = 0x78
REG_INT_MASK = 0x90
REG_CHIP_ID = 0xC0
REG_PHY_STATUS = 0xE6
REG_RX_FRAME_CNT_THRES = 0x9C

RX_VALID_ETH = 0x8008  # Frame is valid and Eth Frame for REG_RX_FHR_STATUS
PHY_STATUS_UP_100TX_FD = 0x4004

REG_CHIP_ID = 0xC0
CHIP_ID = 0x8870


class Ksz8851Eth(BPHandler):

    PADDING = 2
    CRC_SIZE = 4

    def __init__(self, model=EthernetModel):
        BPHandler.__init__(self)
        self.model = model
        self.regs = defaultdict(int)
        self.model.rx_frame_isr = 20
        self.last_rx_time = time.time()

    def get_id(self, qemu):
        return 'ksz8851'

    @bp_handler(['ksz8851_reg_read'])
    def read_reg(self, qemu, bp_addr):
        reg = qemu.regs.r0
        log.debug("Reading Reg %s from pc:%s" % (hex(reg), hex(qemu.regs.lr)))
        if reg == REG_RX_FHR_BYTE_CNT:
            count, length = self.model.get_frame_info(self.get_id(qemu))

            # HAL assumes CRC is included in length, then subtracts that and
            # reads frame without it so inflate length by CRC size
            return True, length + Ksz8851Eth.CRC_SIZE
        elif reg == REG_RX_FHR_STATUS:
            count, length = self.model.get_frame_info(self.get_id(qemu))
            if count > 0:
                return True, RX_VALID_ETH
            else:
                return True, 0
        elif reg == REG_RX_FRAME_CNT_THRES:
            count, length = self.model.get_frame_info(self.get_id(qemu))
            count = 0xFF if count > 0xFF else count
            log.info("Waiting Frams: %i" % count)
            return True, ((count << 8) & 0xFFFF)
        elif reg == REG_PHY_STATUS:
            return True, PHY_STATUS_UP_100TX_FD
        elif reg == REG_CHIP_ID:
            return True, CHIP_ID
        elif reg == REG_TX_MEM_INFO:  # TX Memory available
            return True, 0x1FFF  # Max size
        return True, self.regs[reg]

    @bp_handler(['ksz8851_reg_write'])
    def write_reg(self, qemu, bp_addr):
        reg = qemu.regs.r0
        value = qemu.regs.r1
        self.regs[reg] = value
        log.debug("Writing Reg %i : 0x%x04" % (reg, value))
        if reg == REG_INT_MASK:
            if (value & 0x2000) == 0:
                self.model.disable_rx_isr(self.get_id(qemu))
            else:
                self.model.enable_rx_isr(self.get_id(qemu))

        return True, None

    @bp_handler(['ksz8851_fifo_clrbits'])
    def clr_reg(self, qemu, bp_addr):
        reg = qemu.regs.r0
        value = qemu.regs.r1
        log.debug("Clearing Reg %i : Mask 0x%x04" % (reg, value))
        self.regs[reg] = ((~value) & self.regs[reg]) & 0xFFFF
        return True, None

    @bp_handler(['ksz8851_fifo_setbit'])
    def set_reg(self, qemu, bp_addr):
        reg = qemu.regs.r0
        value = qemu.regs.r1
        log.info("Clearing Reg %i : Mask 0x%x04" % (reg, value))
        self.regs[reg] |= value
        return True, None

    @bp_handler(['ksz8851_fifo_write_begin'])
    def fifo_write_begin(self, qemu, bp_addr):
        log.debug("Write Begin Called")
        self.frame = []
        return True, None

    @bp_handler(['ksz8851_fifo_write'])
    def fifo_write(self, qemu, bp_addr):
        log.debug("Write Called")
        self.frame.append(qemu.read_memory(
            qemu.regs.r0, 1, qemu.regs.r1, raw=True))
        #
        return True, None

    @bp_handler(['ksz8851_fifo_write_end'])
    def fifo_write_end(self, qemu, bp_addr):
        log.debug("Write End Called")
        frame = ''.join(self.frame)
        log.info("Write Called: %s" % binascii.hexlify(frame[0:10]))
        self.model.tx_frame(self.get_id(qemu), frame)
        return True, None

    @bp_handler(['ksz8851_fifo_read'])
    def fifo_read(self, qemu, bp_addr):

        frame = None
        while frame is None:
            log.info("Fifo Read, Blocking")
            frame, rx_time = self.model.get_rx_frame(self.get_id(qemu), True)
        log.info("Frame Received: Delay %s, Frame: %s" %
                 (str(time.time()-rx_time), binascii.hexlify(frame[:10])))
        buf_ptr = qemu.regs.r0
        length = qemu.regs.r1
        log.info("Reading into: %s, %i" % (hex(buf_ptr), length))

        log.info("Inter Frame Timeing: %f" % (time.time()-self.last_rx_time))
        self.last_rx_time = time.time()
        # Frames can have padding to align things in memory add it into
        # front of buffer
        qemu.write_memory(buf_ptr + Ksz8851Eth.PADDING,
                          1, frame, length, raw=True)
        return True, None

    @bp_handler(['ksz8851snl_init'])
    def ksz_return_ok(self, qemu, bp_addr):
        log.info("Init Called")
        return True, 0

    @bp_handler(['ksz8851snl_hard_reset', 'ksz8851snl_interface_init'])
    def ksz_return_void(self, qemu, bp_addr):
        log.info("Init Called")
        return True, None
