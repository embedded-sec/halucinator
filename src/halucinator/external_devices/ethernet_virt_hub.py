# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.

from .ioserver import IOServer
from .trigger_interrupt import SendInterrupt
from threading import Thread, Event
import logging
import time
import socket
import scapy.all as scapy
import os

log = logging.getLogger(__name__)


class HostEthernetServer(Thread):
    def __init__(self, interface, enable_rx=False):
        Thread.__init__(self)
        self.interface = interface
        self.__stop = Event()
        self.enable_rx = enable_rx

        os.system('ip link set %s promisc on' %
                  interface)  # Set to permisucous
        ETH_P_ALL = 3
        self.host_socket = socket.socket(
            socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
        self.host_socket.bind((interface, 0))
        self.host_socket.settimeout(1.0)
        self.handler = None

    def register_topic(self, topic, method):
        log.debug("Registering Host Ethernet Receiver Topic: %s" % topic)
        # self.rx_socket.setsockopt(zmq.SUBSCRIBE, topic)
        self.handler = method

    def run(self):
        while self.enable_rx and not self.__stop.is_set():
            try:
                frame = self.host_socket.recv(2048)
                data = {'interface_id': msg_id, 'frame': frame}
                msg = encode_zmq_msg(topic, data)
                self.handler(self, data)
            except socket.timeout:
                pass

        log.debug("Shutting Down Host Ethernet RX")

    def send_msg(self, topic, msg):
        frame = msg['frame']
        p = scapy.Raw(frame)
        scapy.sendp(p, iface=self.interface)

    def shutdown(self):
        log.debug("Stopping Host Ethernet Server")
        self.__stop.set()


class ViruatalEthHub(object):
    def __init__(self, ioservers=[]):
        '''
            args:
            ioserver:  list of ioservers to bridge together
        '''
        self.ioservers = []
        self.host_socket = None
        self.host_interface = None
        for server in ioservers:
            self.add_server(server)

    def add_server(self, ioserver):
        self.ioservers.append(ioserver)
        ioserver.register_topic('Peripheral.EthernetModel.tx_frame',
                                self.received_frame)

    def received_frame(self, from_server, msg):
        for server in self.ioservers:
            log.info('Forwarding, msg')
            if server != from_server:
                server.send_msg('Peripheral.EthernetModel.rx_frame', msg)

    def shutdown(self):
        for server in self.ioservers:
            log.debug("Eth Hub:Shutting Down")
            server.shutdown()


def main():
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('-r', '--rx_ports', nargs='+', default=[5556, 5558],
                   help='Port numbers to receive zmq messages for IO on')
    p.add_argument('-t', '--tx_ports', nargs='+', default=[5555, 5557],
                   help='Port numbers to send IO messages via zmq, lenght must match --rx_ports')
    p.add_argument('-i', '--interface', required=False, default=None,
                   help='Ethernet Interace to echo data on')
    p.add_argument('-p', '--enable_host_rx', required=False, default=False,
                   action='store_true',
                   help='Enable Recieving data from host interface, requires -i')
    args = p.parse_args()

    if len(args.rx_ports) != len(args.tx_ports):
        print("Number of rx_ports and number of tx_ports must match")
        p.print_usage()
        quit(-1)

    logging.basicConfig()
    #log = logging.getLogger()
    log.setLevel(logging.DEBUG)

    hub = ViruatalEthHub()

    if args.interface is not None:
        host_eth = HostEthernetServer(args.interface, args.enable_host_rx)
        hub.add_server(host_eth)
        host_eth.start()

    for idx, rx_port in enumerate(args.rx_ports):
        print(idx)
        server = IOServer(rx_port, args.tx_ports[idx])
        hub.add_server(server)
        if idx == 0:
            interrupter = SendInterrupt(server)

        server.start()

    time.sleep(2)
    try:
        while(1):
            intr = input("ISR Num:")
            intr = int(intr)
            interrupter.trigger_interrupt(intr)

            pass
    except KeyboardInterrupt:
        pass
    log.info("Shutting Down")
    hub.shutdown()
    # io_server.join()

if __name__ == '__main__':
    main()
