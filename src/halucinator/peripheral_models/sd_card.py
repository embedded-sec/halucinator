# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a
# non-exclusive license for use of this work by or on behalf of the U.S.
# Government. Export of this data may require a license from the United States
# Government.

from .peripheral import requires_tx_map, requires_rx_map, requires_interrupt_map
from . import peripheral_server
from collections import defaultdict
import os
import logging
log = logging.getLogger("SDCardModel")
log.setLevel(logging.DEBUG)

# Register the pub/sub calls and methods that need mapped
# TODO Convert to class that can be instantiated with its parameters
# without requiring every function to be a classmethod
@peripheral_server.peripheral_model
class SDCardModel(object):
    STATES = {'READY': 1}
    BLOCK_SIZE = {}
    filename = {}

    @classmethod
    def set_config(cls, sd_id, filename, block_size):
        cls.BLOCK_SIZE[sd_id] = 0x200
        if filename is not None:
            if peripheral_server.base_dir is not None:
                log.info("Setting File name using output dir")
                cls.filename[sd_id] = os.path.join(
                    peripheral_server.base_dir, filename)
            else:
                log.info("No output found dir")
                cls.filename[sd_id] = filename

    @classmethod
    def get_filename(cls, sd_id):
        if sd_id not in cls.filename:
            if peripheral_server.base_dir is not None:
                cls.filename[sd_id] = os.path.join(
                    peripheral_server.base_dir, "sd_card_%s.bin" % str(sd_id))
            else:
                cls.filename[sd_id] = "sd_card_%s.bin" % str(sd_id)

        return cls.filename[sd_id]

    @classmethod
    def read_block(cls, sd_id, block_num):
        '''
            Reads data from the file, and returns the data if possible 
            return None
        '''
        data = None
        with open(cls.get_filename(sd_id), 'rb') as f:
            addr = block_num * SDCardModel.BLOCK_SIZE[sd_id]
            log.info("SDCardModle Reading: %s" % hex(addr))
            f.seek(addr)
            data = f.read(SDCardModel.BLOCK_SIZE[sd_id])
        return data

    @classmethod
    @requires_tx_map
    def write_block(cls, sd_id, block_num, data):
        '''
            Writes the data to a file, and returns True if no errors else 
            return False
        '''
        filename = cls.get_filename(sd_id)
        if not os.path.exists(filename):
            with open(filename, 'wb') as f:
                pass  # Create the file
        with open(filename, 'rb+') as f:
            addr = block_num * SDCardModel.BLOCK_SIZE[sd_id]
            log.info("SDCardModle Writeing: %s" % hex(addr))
            f.seek(addr)
            f.write(data)
            return True
        return False

    @classmethod
    def get_block_size(cls, sd_id):
        return SDCardModel.BLOCK_SIZE[sd_id]

    @classmethod
    @requires_rx_map
    def get_state(cls, sd_id):
        return SDCardModel.STATES['Ready']
