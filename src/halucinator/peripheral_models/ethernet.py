# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.


from . import peripheral_server
# from peripheral_server import PeripheralServer, peripheral_model
from collections import deque, defaultdict
from .interrupts import Interrupts
import binascii
import struct
import logging
import time
log = logging.getLogger("EthernetModel")
# log.setLevel(logging.DEBUG)


# Register the pub/sub calls and methods that need mapped
@peripheral_server.peripheral_model
class EthernetModel(object):

    frame_queues = defaultdict(deque)
    calc_crc = True
    rx_frame_isr = None
    rx_isr_enabled = False
    frame_times = defaultdict(deque)  # Used to record reception time

    @classmethod
    def enable_rx_isr(cls, interface_id):
        cls.rx_isr_enabled = True
        if cls.frame_queues[interface_id] and cls.rx_frame_isr is not None:
            Interrupts.trigger_interrupt(cls.rx_frame_isr, 'Ethernet_RX_Frame')

    @classmethod
    def disable_rx_isr(self, interface_id):
        EthernetModel.rx_isr_enabled = False

    @classmethod
    @peripheral_server.tx_msg
    def tx_frame(cls, interface_id, frame):
        '''
            Creates the message that Peripheral.tx_msga will send on this 
            event
        '''
        print("Sending Frame (%i): " % len(frame), binascii.hexlify(frame))
        # print ""
        msg = {'interface_id': interface_id, 'frame': frame}
        return msg

    @classmethod
    @peripheral_server.reg_rx_handler
    def rx_frame(cls, msg):
        '''
            Processes reception of this type of message from 
            PeripheralServer.rx_msg
        '''
        interface_id = msg['interface_id']
        log.info("Adding Frame to: %s" % interface_id)
        frame = msg['frame']
        cls.frame_queues[interface_id].append(frame)
        cls.frame_times[interface_id].append(time.time())
        log.info("Adding Frame to: %s" % interface_id)
        if cls.rx_frame_isr is not None and cls.rx_isr_enabled:
            Interrupts.trigger_interrupt(cls.rx_frame_isr, 'Ethernet_RX_Frame')

    @classmethod
    def get_rx_frame(cls, interface_id, get_time=False):
        frame = None
        rx_time = None
        log.info("Checking for: %s" % str(interface_id))
        if cls.frame_queues[interface_id]:
            log.info("Returning frame")
            frame = cls.frame_queues[interface_id].popleft()
            rx_time = cls.frame_times[interface_id].popleft()

        if get_time:
            return frame, rx_time
        else:
            return frame

    @classmethod
    def get_frame_info(cls, interface_id):
        '''
            return number of frames and length of first frame
        '''
        queue = cls.frame_queues[interface_id]
        if queue:
            return len(queue), len(queue[0])
        return 0, 0
