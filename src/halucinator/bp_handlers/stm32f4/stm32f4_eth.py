# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.


from ...peripheral_models.ethernet import EthernetModel
from ..intercepts import tx_map, rx_map
from ..bp_handler import BPHandler, bp_handler
from collections import defaultdict, deque
import struct
import binascii
import os
import logging
log = logging.getLogger(__name__)


class STM32F4Ethernet(BPHandler):

    rx_queues = defaultdict(deque)
    recorder = None

    def __init__(self, model=EthernetModel):
        # Default values from recording
        self.model = model
        self.phy_registers = {1: 0x786d, 0x10: 0x115, 0x11: 0, 0x12: 0x2c00}

    def get_id(self, qemu):
        heth_ptr = qemu.regs.r0
        return qemu.read_memory(heth_ptr, 4, 1)  # heth->Instance

    @bp_handler(['HAL_ETH_TransmitFrame'])
    def handle_tx(self, qemu, bp_addr):
        '''
            Reads the frame out of the emulated device, returns it and an 
            id for the interface(id used if there are multiple ethernet devices)
        '''

        log.info("IN: STM32F4Ethernet.handle_tx")
        heth_ptr = qemu.regs.r0
        length = qemu.regs.r1

        tx_dma_desc = qemu.read_memory(heth_ptr + 44, 4, 1)  # heth->TXDesc
        tx_frame_ptr = qemu.read_memory(
            tx_dma_desc + 8, 4, 1)  # heth->TXDesc->Buffer1Addr
        # *(heth->TXDesc->Buffer1Addr)
        frame = qemu.read_memory(tx_frame_ptr, 1, length, raw=True)
        eth_id = self.get_id(qemu)
        self.model.tx_frame(eth_id, frame)
        return True, 0

    @bp_handler(['HAL_ETH_GetReceivedFrame'])
    def handle_rx(self, qemu, bp_addr):
        avatar = qemu.avatar
        eth_id = self.get_id(qemu)

        log.info("IN: STM32F4Ethernet.handle_rx")
        frame = self.model.get_rx_frame(eth_id)
        heth_ptr = qemu.regs.r0

        DMARxFrameInfos_Addr = heth_ptr + 48
        if frame is not None:
            if avatar.recorder is not None:
                avatar.recorder.save_state_to_db(
                    'HAL_ETH_GetReceivedFrame', is_entry=True)

            log.info("Got Frame: %s" % binascii.hexlify(frame))

            RxDesc_ptr = qemu.read_memory(heth_ptr + 40, 4, 1)

            NextDescAddr = qemu.read_memory(RxDesc_ptr+12, 4, 1)
            BuffAddr = qemu.read_memory(RxDesc_ptr+8, 4, 1)
            FrameInfo = struct.pack(
                '<IIIII', RxDesc_ptr, RxDesc_ptr, 1, len(frame), BuffAddr)
            qemu.write_memory(DMARxFrameInfos_Addr, 1,
                              FrameInfo, len(FrameInfo), raw=True)
            qemu.write_memory(BuffAddr, 1, frame, len(frame), raw=True)
            qemu.write_memory(heth_ptr+40, 4, NextDescAddr, 1)

            if avatar.recorder is not None:
                avatar.recorder.save_state_to_db(
                    'HAL_ETH_GetReceivedFrame', is_entry=False)
            # import os; os.system('stty sane')
            # import IPython; IPython.embed()
        else:  # No Frame available
            # Need to clear out frame to make clear frame was not received
            FrameInfo = struct.pack('<IIIII', 0, 0, 0, 0, 0)
            qemu.write_memory(DMARxFrameInfos_Addr, 1,
                              FrameInfo, len(FrameInfo), raw=True)
        ret_val = 0
        intercept = True
        return intercept, ret_val

    @bp_handler(['HAL_ETH_WritePHYRegister'])
    def write_phy(self, qemu, bp_addr):
        reg = qemu.regs.r1 & 0xFFFF
        self.phy_registers[reg] = qemu.read_memory(qemu.regs.r2, 4, 1)
        return True, 0

    @bp_handler(['HAL_ETH_ReadPHYRegister'])
    def read_phy(self, qemu, bp_addr):
        reg = qemu.regs.r1 & 0xFFFF
        qemu.write_memory(qemu.regs.r2, 4, self.phy_registers[reg], 1)
        return True, 0
