# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a
# non-exclusive license for use of this work by or on behalf of the U.S.
# Government. Export of this data may require a license from the United States
# Government.

from os import sys, path
from ...peripheral_models.uart import UARTPublisher
from ..bp_handler import BPHandler, bp_handler
import logging
log = logging.getLogger("STM32F4UART")
log.setLevel(logging.DEBUG)


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
        huart = qemu.regs.r0
        hw_addr = qemu.read_memory(huart, 4, 1)
        buf_addr = qemu.regs.r1
        buf_len = qemu.regs.r2
        data = qemu.read_memory(buf_addr, 1, buf_len, raw=True)
        log.info("Writing: %s" % data)
        self.model.write(hw_addr, data)
        return True, 0

    # HAL_StatusTypeDef HAL_UART_Receive_IT(UART_HandleTypeDef *huart, uint8_t *pData, uint16_t Size);
    # HAL_StatusTypeDef HAL_UART_Transmit_DMA(UART_HandleTypeDef *huart, uint8_t *pData, uint16_t Size);
    # HAL_StatusTypeDef HAL_UART_Receive_DMA(UART_HandleTypeDef *huart, uint8_t *pData, uint16_t Size);
    @bp_handler(['HAL_UART_Receive', 'HAL_UART_Receive_IT', 'HAL_UART_Receive_DMA'])
    def handle_rx(self, qemu, bp_handler):
        huart = qemu.regs.r0
        hw_addr = qemu.read_memory(huart, 4, 1)
        size = qemu.regs.r2
        log.info("Waiting for data: %i" % size)
        data = self.model.read(hw_addr, size, block=True)
        log.info("Got Data: %s" % data)

        qemu.write_memory(qemu.regs.r1, 1, data, size, raw=True)
        return True, 0
