# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a
# non-exclusive license for use of this work by or on behalf of the U.S.
# Government. Export of this data may require a license from the United States
# Government.

import binascii
from .ioserver import IOServer
from .trigger_interrupt import SendInterrupt
import logging
import time
import socket
log = logging.getLogger("ViruatalEthHub")
log.setLevel(logging.DEBUG)


class IEEE802_15_4(object):
    def __init__(self, ioservers=[]):
        '''
            args:
            ioserver:  list of ioservers to bridge together
        '''
        self.ioservers = []
        self.host_socket = None
        for server in ioservers:
            self.add_server(server)

    def add_server(self, ioserver):
        self.ioservers.append(ioserver)
        ioserver.register_topic('Peripheral.IEEE802_15_4.tx_frame',
                                self.received_frame)

    def received_frame(self, from_server, msg):
        for server in self.ioservers:
            if server != from_server:
                log.info('Forwarding, msg')
                server.send_msg('Peripheral.IEEE802_15_4.rx_frame', msg)
        if self.host_socket is not None:
            frame = msg['frame']
            self.host_socket.send(frame)

    def shutdown(self):
        for server in self.ioservers:
            server.shutdown()


if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('-r', '--rx_ports', nargs='+', default=[5556, 5558],
                   help='Port numbers to receive zmq messages for IO on')
    p.add_argument('-t', '--tx_ports', nargs='+', default=[5555, 5557],
                   help='Port numbers to send IO messages via zmq, length must match --rx_ports')
    p.add_argument('-l', '--logs', nargs='+', default=['Receiver.txt', 'Sender.txt'],
                   help='Log files to write IO frames to, length must match --rx_ports')
    args = p.parse_args()

    if len(args.rx_ports) != len(args.tx_ports):
        print("Number of rx_ports and number of tx_ports must match")
        p.print_usage()
        quit(-1)

    logging.basicConfig()
    #log = logging.getLogger()
    log.setLevel(logging.DEBUG)

    hub = IEEE802_15_4()

    for idx, rx_port in enumerate(args.rx_ports):
        print(idx)
        server = IOServer(rx_port, args.tx_ports[idx], args.logs[idx])
        hub.add_server(server)
        server.start()

    time.sleep(2)
    try:
        msg = {"id": 'rf233', 'frame': None}
        while(1):
            frame = input("Enter Hexlified Frame")
            msg['frame'] = binascii.unhexlify(frame)
            hub.received_frame(None, msg)
    except KeyboardInterrupt:
        pass
    log.info("Shutting Down")
    hub.shutdown()
    # io_server.join()
