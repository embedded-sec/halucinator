# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.

from os import sys, path
from ...peripheral_models.uart import UARTPublisher
from ..bp_handler import BPHandler, bp_handler
import logging
log = logging.getLogger(__name__)

from ... import hal_log
hal_log = hal_log.getHalLogger()


class STM32F4UART(BPHandler):

    def __init__(self, impl=UARTPublisher):
        self.model = impl

    @bp_handler(['HAL_UART_Init'])
    def hal_ok(self, qemu, bp_addr):
        log.info("Init Called")
        return True, 0

    @bp_handler(['HAL_UART_GetState'])
    def get_state(self, qemu, bp_addr):
        log.info("Get State")
        return True, 0x20  # 0x20 READY

    @bp_handler(['HAL_UART_Transmit', 'HAL_UART_Transmit_IT', 'HAL_UART_Transmit_DMA'])
    def handle_tx(self, qemu, bp_addr):
        '''
            Reads the frame out of the emulated device, returns it and an 
            id for the interface(id used if there are multiple ethernet devices)
        '''
        huart = qemu.get_arg(0)
        hw_addr = qemu.read_memory(huart, 4, 1)
        buf_addr = qemu.get_arg(1)
        buf_len = qemu.get_arg(2)
        data = qemu.read_memory(buf_addr, 1, buf_len, raw=True)
        hal_log.info("UART %i TX:%s" % (hw_addr, data))
        self.model.write(hw_addr, data)
        return True, 0

    # HAL_StatusTypeDef HAL_UART_Receive_IT(UART_HandleTypeDef *huart, uint8_t *pData, uint16_t Size);
    # HAL_StatusTypeDef HAL_UART_Transmit_DMA(UART_HandleTypeDef *huart, uint8_t *pData, uint16_t Size);
    # HAL_StatusTypeDef HAL_UART_Receive_DMA(UART_HandleTypeDef *huart, uint8_t *pData, uint16_t Size);
    @bp_handler(['HAL_UART_Receive', 'HAL_UART_Receive_IT', 'HAL_UART_Receive_DMA'])
    def handle_rx(self, qemu, bp_handler):
        huart = qemu.get_arg(0)
        hw_addr = qemu.read_memory(huart, 4, 1)
        size = qemu.get_arg(2)
        log.info("Waiting for data: %i" % size)
        data = self.model.read(hw_addr, size, block=True)
        hal_log.info("UART %i RX: %s" % (hw_addr, data))

        qemu.write_memory(qemu.get_arg(1), 1, data, size, raw=True)
        return True, 0
