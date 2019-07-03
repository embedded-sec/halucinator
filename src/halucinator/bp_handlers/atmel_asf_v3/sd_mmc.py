# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a
# non-exclusive license for use of this work by or on behalf of the U.S.
# Government. Export of this data may require a license from the United States
# Government.


from ...peripheral_models.sd_card import SDCardModel
from ..bp_handler import BPHandler, bp_handler
from collections import defaultdict, deque
import struct
import binascii
import os
import logging
log = logging.getLogger("SD-MMC")
log.setLevel(logging.DEBUG)

# sd_mmc_err_t;
SD_MMC_OK = 0   # No error
SD_MMC_INIT_ONGOING = 1   # Card not initialized
SD_MMC_ERR_NO_CARD = 2   # No SD/MMC card inserted
SD_MMC_ERR_UNUSABLE = 3   # Unusable card
SD_MMC_ERR_SLOT = 4   # Slot unknow
SD_MMC_ERR_COMM = 5   # General communication error
SD_MMC_ERR_PARAM = 6   # Illeage input parameter
SD_MMC_ERR_WP = 7   # Card write protected

# card_type_t;
CARD_TYPE_UNKNOWN = (0)      # Unknown type card
CARD_TYPE_SD = (1 << 0)  # SD card
CARD_TYPE_MMC = (1 << 1)  # MMC card
CARD_TYPE_SDIO = (1 << 2)  # SDIO card
CARD_TYPE_HC = (1 << 3)  # High capacity card
# SD combo card (io + memory)
CARD_TYPE_SD_COMBO = (CARD_TYPE_SD | CARD_TYPE_SDIO)


class SDCard(BPHandler):

    # Just let these execute
    # uint8_t sd_mmc_nb_slot(void);

    def __init__(self, model=SDCardModel):
        self.model = model
        self.slot_configs = {0: {'capacity': 512*1024, 'block_size': 512,
                                 'write_protected': False, 'filename': 'sd_image.img'}}

        for sd_id, values in list(self.slot_configs.items()):
            self.model.set_config(sd_id, values['filename'],
                                  values['block_size'])

    def register_handler(self, addr, func_name, slots=None):
        '''
            slots(dict): {slot_id: {'capactiy': int (KB), 'block_size': int, 
                                    'write_protected': bool, 'filename': file}}
        '''
        if slots is not None:
            self.slot_configs = slots
            for sd_id, values in list(slots.items()):
                self.model.set_config(sd_id, values['filename'],
                                      values['block_size'])
        return BPHandler.register_handler(self, addr, func_name)

    @bp_handler(['sd_mmc_init'])
    def log_only(self, qemu, bp_addr):
        # void sd_mmc_init(void);
        log.info("SD_MMC_INIT Executed")
        log.info("LR: %s", hex(qemu.regs.lr))
        return False, None

    @bp_handler(['sd_mmc_check'])
    def check(self, qemu, bp_addr):
        # sd_mmc_err_t sd_mmc_check(uint8_t slot);
        log.info("SD_MMC_Check Executed")
        log.info("LR: %s", hex(qemu.regs.lr))
        return True, 0

    @bp_handler(['sd_mmc_get_type'])
    def get_sd_type(self, qemu, bp_addr):
        # card_type_t sd_mmc_get_type(uint8_t slot);
        log.info("Get SD Type Executed")
        log.info("LR: %s", hex(qemu.regs.lr))
        return True, CARD_TYPE_SD

    @bp_handler(['sd_mmc_get_type'])
    def get_sd_version(self, qemu, bp_addr):
        # card_version_t sd_mmc_get_version(uint8_t slot);
        log.info("Get SD Version")
        log.info("LR: %s", hex(qemu.regs.lr))
        return True, 0x20  # Version 2.00

    @bp_handler(['sd_mmc_get_capacity'])
    def get_capacity(self, qemu, bp_addr):
         # uint32_t sd_mmc_get_capacity(uint8_t slot);
        slot = qemu.regs.r0 & 0xFF
        log.info("Get SD Get Capacity: Slot %i, Size %i" %
                 (slot, self.slot_configs[slot]['capacity']))
        log.info("LR: %s", hex(qemu.regs.lr))
        return True, self.slot_configs[slot]['capacity']

    @bp_handler(['sd_mmc_is_write_protected'])
    def is_write_protected(self, qemu, bp_addr):
        # bool sd_mmc_is_write_protected(uint8_t slot);
        slot = qemu.regs.r0 & 0xFF
        log.info("IS Write Protected: Slot %i, value: %s" %
                 (slot, self.slot_configs[slot]['write_protected']))
        log.info("LR: %s", hex(qemu.regs.lr))
        return True, self.slot_configs[slot]['write_protected']

    @bp_handler(['sd_mmc_init_read_blocks'])
    def init_read(self, qemu, bp_addr):
        # sd_mmc_err_t sd_mmc_init_read_blocks(uint8_t slot, uint32_t start,
        # 	uint16_t nb_block);
        slot = qemu.regs.r0 & 0xFF
        self.active_read_slot = slot & 0xFF
        self.active_read_block = qemu.regs.r1
        self.nb_blocks = qemu.regs.r2 & 0xFFFF
        log.info("Init Read: Slot %i, Block Num %i, #Blocks: 0x%08x" %
                 (slot,  self.active_read_block, self.nb_blocks))
        log.info("LR: %s", hex(qemu.regs.lr))
        return True, 0

    @bp_handler(['sd_mmc_start_read_blocks'])
    def read_blocks(self, qemu, bp_addr):
        # sd_mmc_err_t sd_mmc_start_read_blocks(void *dest, uint16_t nb_block);
        dest = qemu.regs.r0
        number_blocks = qemu.regs.r1 & 0xFFFF
        log.info("Read: Block Num 0x%08x, #Blocks: %i" %
                 (dest, number_blocks))
        log.info("LR: %s", hex(qemu.regs.lr))

        blocks = []
        for i in range(number_blocks):
            blocks.append(self.model.read_block(self.active_read_slot,
                                                self.active_read_block))
            self.active_read_block += 1
        data = ''.join(blocks)
        qemu.write_memory(dest, 1, data, len(data), raw=True)

        return True, 0

    @bp_handler(['sd_mmc_wait_end_of_read_blocks'])
    def end_read_blocks(self, qemu, bp_addr):
        # sd_mmc_err_t sd_mmc_wait_end_of_read_blocks(bool abort);
        log.info("End Read Blocks")
        log.info("LR: %s", hex(qemu.regs.lr))
        self.active_read_block = None
        self.active_read_slot = None
        return True, 0

    @bp_handler(['sd_mmc_init_write_blocks'])
    def init_write(self, qemu, bp_addr):
        # sd_mmc_err_t sd_mmc_init_write_blocks(uint8_t slot, uint32_t start,
            # 	uint16_t nb_block);
        slot = qemu.regs.r0 & 0xFF
        self.active_write_slot = slot
        self.active_write_block = qemu.regs.r1
        self.nb_blocks = qemu.regs.r2
        log.info("Init Write: Slot %i, Block Num %i, #Blocks: %i" %
                 (slot, self.active_write_block, self.nb_blocks))
        log.info("LR: %s", hex(qemu.regs.lr))
        return True, 0

    @bp_handler(['sd_mmc_start_write_blocks'])
    def write_blocks(self, qemu, bp_addr):
       # sd_mmc_err_t sd_mmc_start_write_blocks(const void *src, uint16_t nb_block);
        src_ptr = qemu.regs.r0
        nb_blocks = qemu.regs.r1 & 0xFFFF

        log.info("Write: Slot SRC 0x%08x, #Blocks: %i" %
                 (src_ptr, nb_blocks))
        log.info("LR: %s", hex(qemu.regs.lr))

        block_size = self.slot_configs[self.active_write_slot]['block_size']
        for i in range(nb_blocks):
            addr = i * block_size
            data = qemu.read_memory(addr, 1, block_size, raw=True)
            self.model.write_block(self.active_write_slot,
                                   self.active_write_block, data)
            self.active_write_block += 1

        return True, 0

    @bp_handler(['sd_mmc_wait_end_of_write_blocks'])
    def end_write_blocks(self, qemu, bp_addr):
        # sd_mmc_err_t sd_mmc_wait_end_of_write_blocks(bool abort);
        log.info("End Write Blocks")
        log.info("LR: %s", hex(qemu.regs.lr))
        self.active_write_slot = None
        self.active_write_block = None
        return True, 0
