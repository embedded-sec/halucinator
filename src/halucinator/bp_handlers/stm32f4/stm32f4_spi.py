# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. 
# Government retains certain rights in this software.

from ...peripheral_models.spi import SPIPublisher
from ..bp_handler import BPHandler, bp_handler
import logging

log = logging.getLogger(__name__)

# TODO: Callbacks


class STM32F4SPI(BPHandler):

    def __init__(self, impl=SPIPublisher):
        self.model = impl

    @bp_handler(['HAL_SPI_Init'])
    def hal_ok(self, qemu, bp_addr):
        log.info("SPI Init Called")
        return True, 0

    @bp_handler(['HAL_SPI_DeInit'])
    def hal_ok_2(self, qemu, bp_addr):
        log.info("SPI DeInit Called")
        return True, 0

    @bp_handler(['HAL_SPI_GetState'])
    def get_state(self, qemu, bp_addr):
        log.info("SPI Get State")
        return True, 0x20  # 0x20 READY

    @bp_handler(['HAL_SPI_Transmit', 'HAL_SPI_Transmit_IT', 'HAL_SPI_Transmit_DMA'])
    def handle_tx(self, qemu, bp_addr):
        '''
            Reads the frame out of the emulated device, returns it and an
            id for the interface(id used if there are multiple ethernet devices)
        '''
        hspi = qemu.regs.r0
        hw_addr = qemu.read_memory(hspi, 4, 1)
        buf_addr = qemu.regs.r1
        buf_len = qemu.regs.r2
        data = qemu.read_memory(buf_addr, 1, buf_len, raw=True)
        log.info("Writing: %s" % data)
        self.model.write(hw_addr, data)
        return True, 0

    @bp_handler(['HAL_SPI_Receive', 'HAL_SPI_Receive_IT', 'HAL_SPI_Receive_DMA'])
    def handle_rx(self, qemu, bp_handler):
        hspi = qemu.regs.r0
        hw_addr = qemu.read_memory(hspi, 4, 1)
        size = qemu.regs.r2
        log.info("Waiting for data: %i" % size)
        data = self.model.read(hw_addr, size, block=True)
        log.info("Got Data: %s" % data)

        qemu.write_memory(qemu.regs.r1, 1, data, size, raw=True)
        return True, 0

    @bp_handler(['HAL_SPI_TransmitReceive', 'HAL_SPI_TransmitReceive_IT', 'HAL_SPI_TransmitReceive_DMA'])
    def handle_txrx(self, qemu, bp_addr):
        '''
        Does a combo tx/rx, in blocking mode

        :param qemu:
        :param bp_addr:
        :return:
        '''
        hspi = qemu.regs.r0
        hw_addr = qemu.read_memory(hspi, 4, 1)
        size = qemu.regs.r3

        tx_buf_addr = qemu.regs.r1
        tx_data = qemu.read_memory(tx_buf_addr, 1, buf_len, raw=True)
        log.info("Writing: %s" % data)
        self.model.write(hw_addr, tx_data)

        # TODO: Timeout
        rx_buf_addr = qemu.regs.r2
        log.info("Waiting for data: %i" % size)
        rx_data = self.model.read(hw_addr, size, block=True)
        log.info("Got Data: %s" % rx_data)
        qemu.write_memory(qemu.regs.r1, 1, rx_data, size, raw=True)
        return True, 0
