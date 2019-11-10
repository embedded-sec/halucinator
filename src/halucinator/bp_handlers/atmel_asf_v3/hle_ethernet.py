Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains certain rights in this software.


import IPython
from ...peripheral_models.ethernet import EthernetModel
from ..intercepts import tx_map, rx_map
from ..bp_handler import BPHandler, bp_handler
from collections import defaultdict, deque
import struct
import binascii
import os
import logging
import time
log = logging.getLogger("HLE_Ethernet")
log.setLevel(logging.INFO)


# netif Offsets
NETIF_STATE = 32
NETIF_INPUT = 16

# struct ksz8851snl_device Offsets
NUM_RX_BUFFS = 2
NUM_TX_BUFFS = 2

DEVICE_RX_DESC = 0
DEVICE_TX_DESC = 4 * NUM_RX_BUFFS
DEVICE_RX_PBUF = DEVICE_TX_DESC + (4 * NUM_TX_BUFFS)
DEVICE_TX_PBUF = DEVICE_RX_PBUF + (4 * NUM_RX_BUFFS)
DEVICE_RX_HEAD = DEVICE_TX_PBUF + (4 * NUM_TX_BUFFS)
DEVICE_RX_TAIL = DEVICE_RX_HEAD + 4
DEVICE_TX_HEAD = DEVICE_RX_TAIL + 4
DEVICE_TX_TAIL = DEVICE_TX_HEAD + 4
DEVICE_NETIF = DEVICE_TX_TAIL + 4

# pbuf offsets
PBUF_NEXT = 0
PBUF_PAYLOAD = 4
PBUF_TOT_LEN = 8
PBUF_LEN = 10
PBUF_TYPE = 12
PBUF_FLAGS = 13
PBUF_REF = 14

# Ethernet Types
ETHTYPE_ARP = 0x0806
ETHTYPE_IP = 0x0800

PADDING = 2   # Padding used on ethernet frames to keep alignment

SUPPORTED_TYPES = (ETHTYPE_ARP, ETHTYPE_IP)


class Ksz8851HLE(BPHandler):

    def __init__(self, model=EthernetModel):
        BPHandler.__init__(self)
        self.model = model
        self.last_rx_time = time.time()
        self.last_exec_time = time.time()
        self.dev_ptr = None
        self.netif_ptr = None

    def is_supported_frame_type(self, frame):
        ty = struct.unpack('!H', frame[12:14])[0]
        log.info("Frame ty: %s" % hex(ty))
        log.info("Frame : %s" % binascii.hexlify(frame[:20]))
        return ty in (SUPPORTED_TYPES)

    def get_id(self, qemu):
        return 'ksz8851'

    @bp_handler(['sys_get_ms'])
    def sys_get_ms(self, qemu, bp_addr):
        return True, 0

    def call_populate_queues(self, qemu):
        '''
        This will call the ksz8851snl_rx_populate_queue
        returning to ethernetif_input
        '''
        self.org_lr = qemu.regs.lr
        qemu.regs.r0 = self.dev_ptr
        # Make sure thumb bit is set, lr already saved on stack
        qemu.regs.lr = qemu.regs.pc | 1
        qemu.regs.pc = qemu.avatar.callables['ksz8851snl_rx_populate_queue'] | 1

    @bp_handler(['ethernetif_input'])
    def ethernetif_input(self, qemu, bp_addr):
        # 1. See if there are frames
        now = time.time()
        log.info("In ETHERNET_INPUT: %f" % (now - self.last_exec_time))
        self.last_exec_time = time.time()

        start_time = time.time()
        (num_frames, size_1st_frame) = self.model.get_frame_info(self.get_id(qemu))
        if num_frames > 0:
            if self.netif_ptr is None:
                # Will be none if not returning from populate_queues
                self.netif_ptr = qemu.regs.r0
                self.dev_ptr = qemu.read_memory(
                    self.netif_ptr + NETIF_STATE, 4, 1)
            else:  # Executing on return from popluate_queues
                qemu.regs.lr = self.org_lr

            # Get Pbuf, if null use populate_queues to allocate new ones
            rx_pbuf_ptr = qemu.read_memory(self.dev_ptr + DEVICE_RX_PBUF, 4, 1)
            if rx_pbuf_ptr == 0:
                self.call_populate_queues(qemu)
                log.info("Execution Time pop_queues %f " %
                         (time.time()-start_time))
                return False, None

            frame, rx_time = self.model.get_rx_frame(self.get_id(qemu), True)
            if frame != None and self.is_supported_frame_type(frame):
                # Remove pbuf addr from hw buffers. Allows new one to be made
                # and this one to be freed by stack
                qemu.write_memory(self.dev_ptr + DEVICE_RX_PBUF, 4, 0, 1)

                self.last_rx_time = time.time()

                # Get payload_ptr
                payload_ptr = qemu.read_memory(rx_pbuf_ptr+PBUF_PAYLOAD, 4, 1)
                log.info("Pbuf->payload : %s->%s" %
                         (hex(rx_pbuf_ptr), hex(payload_ptr)))

                # Write to memory
                qemu.write_memory(payload_ptr + PADDING, 1,
                                  frame, len(frame), raw=True)
                qemu.write_memory(rx_pbuf_ptr+PBUF_TOT_LEN, 2, len(frame), 1)
                qemu.write_memory(rx_pbuf_ptr+PBUF_LEN, 2, len(frame), 1)

                # Get input function, and call it
                input_fn_ptr = qemu.read_memory(
                    self.netif_ptr + NETIF_INPUT, 4, 1)
                # Call netif->input
                log.info("Calling %s" % hex(input_fn_ptr))
                qemu.regs.r0 = rx_pbuf_ptr
                qemu.regs.r1 = self.netif_ptr
                qemu.regs.pc = input_fn_ptr
                self.dev_ptr = None
                self.netif_ptr = None
                log.info("Got Frame: LATENCY %f, inter packet time %f" %
                         (time.time()-rx_time, (time.time() - self.last_rx_time)))
                log.info("Execution Time rx_packet %f " %
                         (time.time()-start_time))
                return False, None
        self.dev_ptr = None
        self.netif_ptr = None
        log.info("Execution Time no frame %f " % (time.time()-start_time))
        return True, None

    @bp_handler(['ksz8851snl_low_level_output'])
    def low_level_output(self, qemu, bp_addr):
        log.info('In low level output')
        pbuf_free = qemu.avatar.callables['pbuf_free']
        pbuf_ptr = qemu.regs.r1
        frame_bufs = []
        p = pbuf_ptr
        # os.system('stty sane') # Make so display works
        # IPython.embed()
        padding = PADDING
        while p != 0:
            length = qemu.read_memory(p + PBUF_LEN, 2, 1)
            payload_ptr = qemu.read_memory(p + PBUF_PAYLOAD, 4, 1)
            frame_bufs.append(qemu.read_memory(
                payload_ptr + padding, 1, length-padding, raw=True))
            padding = 0  # Padding only on first pbuf
            p = qemu.read_memory(p+PBUF_NEXT, 4, 1)

        frame = ''.join(frame_bufs)
        log.info("Sending Frame with size: %s" % (len(frame)))
        self.model.tx_frame(self.get_id(qemu), frame)
        #qemu.call_ret_0(pbuf_free, pbuf_ptr)
        return True, 0

    @bp_handler(['ksz8851snl_init'])
    def return_ok(self, qemu, bp_addr):
        log.info("Init Called")
        return True, 0
