# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.


from ...peripheral_models.ieee802_15_4 import IEEE802_15_4
from ..intercepts import tx_map, rx_map
from ..bp_handler import BPHandler, bp_handler
from collections import defaultdict, deque
import struct
import binascii
import os
import logging
import time
log = logging.getLogger("SAMR21-Radio")
log.setLevel(logging.DEBUG)

# SPI Addresses
REG_TRX_STATUS = 0x01
REG_TRX_STATE = 0x02
REG_TRX_CTRL_1 = 0x04  # Default = 0x22
REG_PART_NUM = 0x1C    # Reset 0x0B
REG_VERSION_NUM = 0x1D  # Reset 0x02
REG_MAN_ID_0 = 0x1E  # 0x1F
REG_MAN_ID_1 = 0x1F  # 0x00
STATE_TRX_OFF = 0x08
TRXCMD_PLL_ON = 0x09
STATE_RX_ON = 0x06

# IRQ Status regs and flags, reading from register clears values
REG_IRQ_MASK = 0x0E  # 0 Disabled, 1 enabled
REG_IRQ_STATUS = 0x0F
IRQ_BAT_LOW = 1 << 7
IRQ_TRX_UR = 1 << 6
IRQ_ADDR_MATCH = 1 << 5
IRQ_CCA_ED_DONE = 1 << 4
IRQ_TRX_END = 1 << 3
IRQ_RX_START = 1 << 2
IRQ_PLL_UNLOCK = 1 << 1
IRQ_PLL_LOCK = 1

TRX_STATUS_P_ON = 0x00
TRX_STATUS_BUSY_RX = 0x01
TRX_STATUS_RX_ON = 0x06
TRX_STATUS_TRX_OFF = 0x08
TRX_STATUS_TX_ON = 0x09
TRX_STATUS_SLEEP = 0x0f
TRX_STATUS_PREP_DEEP_SLEEP = 0x10
TRX_STATUS_BUSY_RX_AACK = 0x11
TRX_STATUS_BUSY_TX_ARET = 0x12
TRX_STATUS_RX_AACK_ON = 0x16
TRX_STATUS_TX_ARET_ON = 0x12

RF233_REG_TRX_STATE = 0x02
RX_ENABLE = 0


class SAMR21Radio(BPHandler):

    PADDING = 2
    CRC_SIZE = 4

    def __init__(self, model=IEEE802_15_4):
        BPHandler.__init__(self)
        self.model = model
        self.regs = defaultdict(int)
        self.model.rx_frame_isr = 20
        self.last_rx_time = time.time()

    def get_id(self, qemu):
        return 'SAMR21Radio'

    @bp_handler(['trx_reg_read'])
    def read_reg(self, qemu, bp_addr):
        # uint8_t trx_reg_read(uint8_t addr);
        reg = qemu.regs.r0
        # log.debug("Reading Reg %s from pc:%s" % (hex(reg),hex(qemu.regs.lr)))
        return True, self.regs[reg]

    @bp_handler(['trx_reg_write'])
    def write_reg(self, qemu, bp_addr):
        # void trx_reg_write(uint8_t addr, uint8_t data);
        reg = qemu.regs.r0
        value = qemu.regs.r1
        # log.debug("Write Reg %s from pc:%s" % (hex(reg),hex(qemu.regs.lr)))
        if reg == RF233_REG_TRX_STATE:
            self.regs[RF233_REG_TRX_STATE] = value

        return True, None

    @bp_handler(['trx_bit_read'])
    def read_bit(self, qemu, bp_addr):
        # uint8_t trx_bit_read(uint8_t addr, uint8_t mask, uint8_t pos);
        reg = qemu.regs.r0
        log.debug("Read Bit %s from pc:%s" % (hex(reg), hex(qemu.regs.lr)))
        return True, None

    @bp_handler(['trx_bit_write'])
    def write_bit(self, qemu, bp_addr):
        # void trx_bit_write(uint8_t reg_addr, uint8_t mask, uint8_t pos,
        # 		uint8_t new_value);
        reg = qemu.regs.r0
        log.debug("Write Bit %s from pc:%s" % (hex(reg), hex(qemu.regs.lr)))
        return True, None

    @bp_handler(['trx_frame_read'])
    def read_frame(self, qemu, bp_addr):
        # void trx_frame_read(uint8_t *data, uint8_t length);
        data_ptr = qemu.regs.r0
        length = qemu.regs.r1
        log.info("Read Frame %s , len %i" % (hex(data_ptr), length))
        if self.model.has_frame():
            frame, rx_time = self.model.get_first_frame(True)
            if length < len(frame):
                qemu.write_memory(data_ptr, 1, frame, len(frame))
        return True, None

    @bp_handler(['trx_frame_write'])
    def write_frame(self, qemu, bp_addr):
        # void trx_frame_write(uint8_t *data, uint8_t length);
        data_ptr = qemu.regs.r0
        length = qemu.regs.r1
        log.info("Write Frame %s , len %i" % (hex(data_ptr), length))
        frame = qemu.read_memory(data_ptr, 1, length, raw=True)
        self.model.tx_frame(self.get_id(qemu), frame)
        return True, None

    @bp_handler(['trx_sram_read'])
    def sram_read(self, qemu, bp_addr):
        # void trx_sram_read(uint8_t addr, uint8_t *data, uint8_t length);
        data_ptr = qemu.regs.r0
        log.info("SRAM Read %s , len %i" % (hex(data_ptr), qemu.regs.r1))
        return True, None

    @bp_handler(['trx_sram_write'])
    def sram_write(self, qemu, bp_addr):
         # void trx_sram_write(uint8_t addr, uint8_t *data, uint8_t length);
        data_ptr = qemu.regs.r0
        log.info("SRAM Write %s , len %i" % (hex(data_ptr), qemu.regs.r1))
        return True, None

    @bp_handler(['trx_aes_wrrd'])
    def aes_wrrd(self, qemu, bp_addr):
        # void trx_aes_wrrd(uint8_t addr, uint8_t *idata, uint8_t length);
        data_ptr = qemu.regs.r0
        log.info("SRAM Write %s , len %i" % (hex(data_ptr), qemu.regs.r1))
        return True, None

    # void trx_spi_done_cb_init(void *spi_done_cb);
    # void trx_spi_init(void);  Likely needs to execute to set call back

    @bp_handler(['PhyReset'])
    def nop_return_void(self, qemu, bp_addr):
         # void PhyReset(void);
        log.info("Init Called")
        return True, None
