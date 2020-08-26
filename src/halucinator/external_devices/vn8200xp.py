# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. 
# Government retains certain rights in this software.

import IPython
import threading
import zmq
from ..peripheral_models.peripheral_server import encode_zmq_msg, decode_zmq_msg
from .ioserver import IOServer
import logging

log = logging.getLogger(__main__)
log.setLevel(logging.DEBUG)


class VN8200XP(Thread):
    def __init__(self, ioserver):
        self.ioserver = ioserver
        ioserver.register_topic(
            'Peripheral.UARTPublisher.write', self.write_handler)

    def write_handler(self, ioserver, msg):
        print((msg,))
        IPython.embed()

    def send_data(self, id, chars):
        d = {'id': id, 'chars': chars}
        log.debug("Sending Message %s" % (str(d)))
        self.ioserver.send_msg('Peripheral.UARTPublisher.rx_data', d)


if __name__ == '__main__':
    from argparse import ArgumentParser

    p = ArgumentParser()
    p.add_argument('-r', '--rx_port', default=5556,
                   help='Port number to receive zmq messages for IO on')
    p.add_argument('-t', '--tx_port', default=5555,
                   help='Port number to send IO messages via zmq')
    p.add_argument('-i', '--id', default=0x20000ab0, type=int,
                   help="Id to use when sending data")
    args = p.parse_args()

    import halucinator.hal_log as hal_log
    hal_log.setLogConfig()

    io_server = IOServer(args.rx_port, args.tx_port)
    uart = UARTPrintServer(io_server)

    io_server.start()

    try:
        while (1):
            data = input("Data:")
            log.debug("Got %s" % str(data))
            if data == '\\n':
                data = '\n\r'
            elif data == '':
                break
            # d = {'id':args.id, 'data': data}
            uart.send_data(args.id, data)
    except KeyboardInterrupt:
        pass
    log.info("Shutting Down")
    io_server.shutdown()
    # io_server.join()
