# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. 
# Government retains certain rights in this software.


from . import peripheral_server
# from queue import Queue
from threading import Event, Thread
from collections import deque, defaultdict
import sys
import logging
from itertools import repeat
import time

log = logging.getLogger(__name__)

class UARTModel(object):

    def __init__(self):
        self.tx_buffer = deque()
        self.rx_buffer = deque()

    def read(self, count, blocking=True):
        log.info("Reading %d bytes" % count)
        out = b""
        if self.rx_buffer:
            while True:
                data_pkt = self.rx_buffer.pop()
                l += min(len(data_pkt), count - bytes_read)
                out += data_pkt[:l]
                if l < len(data_pkt):
                    leftover = data_pkt[l:]
                    self.rx_buffer.appendleft(leftover)
                if bytes_read == count:
                    break
        return out

    def write(self, data):
        log.info("Writing %d bytes" % len(data))
        self.tx_buffer.append(data)

    def tx_empty(self):
        return self.tx_buffer.empty()

    def rx_empty(self):
        return self.rx_buffer.empty()


# Register the pub/sub calls and methods that need mapped
@peripheral_server.peripheral_model
class SPIPublisher(object):
    rx_buffers = defaultdict(deque)

    @classmethod
    @peripheral_server.tx_msg
    def write(cls, spi_id, chars):
        '''
           Publishes the data to sub/pub server
        '''
        log.debug("In: SPIPublisher.write")
        msg = {'id': uart_id, 'chars': chars}
        return msg

    @classmethod
    def read(cls, spi_id, count=1, block=False):
        '''
            Gets data previously received from the sub/pub server
            Args:
                spi_id:   A unique id for the spi
                count:  Max number of chars to read
                block(bool): Block if data is not available
        '''
        log.debug("In: SPIPublisher.read id:%s count:%i, block:%s" %
                  (hex(spi_id), count, str(block)))
        while block and (len(cls.rx_buffers[spi_id]) < count):
            pass
        log.debug("Done Blocking: SPIPublisher.read")
        buffer = cls.rx_buffers[spi_id]
        chars_available = len(buffer)
        if chars_available >= count:
            chars = list(map(apply, repeat(buffer.popleft, count)))
            chars = ''.join(chars)
        else:
            chars = list(map(apply, repeat(buffer.popleft, chars_available)))
            chars = ''.join(chars)

        return chars

    @classmethod
    @peripheral_server.reg_rx_handler
    def rx_data(cls, msg):
        '''
            Handles reception of these messages from the PeripheralServer
        '''
        log.debug("SPI rx_data got message: %s" % str(msg))
        spi_id = msg['id']
        data = msg['chars']
        cls.rx_buffers[spi_id].extend(data)