# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.

from .ioserver import IOServer
from .IEEE802_15_4 import IEEE802_15_4
from .ethernet_virt_hub import ViruatalEthHub, HostEthernetServer

import logging
import time
log = logging.getLogger(__name__)


if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('-r', '--rx_ports', nargs='+', default=[5556, 5558],
                   help='Port numbers to receive zmq messages for IO on')
    p.add_argument('-t', '--tx_ports', nargs='+', default=[5555, 5557],
                   help='Port numbers to send IO messages via zmq, lenght must match --rx_ports')
    p.add_argument('-i', '--interface', required=False, default=None,
                   help='Ethernet Interace to echo data on')
    p.add_argument('-l', '--listen_to_host', required=False, default=False,
                   action='store_true',
                   help='Enable Recieving data from host interface, requires -i')
    args = p.parse_args()

    if len(args.rx_ports) != len(args.tx_ports):
        print("Number of rx_ports and number of tx_ports must match")
        p.print_usage()
        quit(-1)

    import halucinator.hal_log as hal_log
    hal_log.setLogConfig()

    ethernet_hub = ViruatalEthHub()

    # TODO create additional wireless hubs to create different topologies
    wireless_hub = IEEE802_15_4()

    if args.interface is not None:
        host_eth = HostEthernetServer(args.interface, args.listen_to_host)
        ethernet_hub.add_server(host_eth)
        host_eth.start()

    for idx, rx_port in enumerate(args.rx_ports):
        print(idx)
        server = IOServer(rx_port, args.tx_ports[idx])
        wireless_hub.add_server(server)
        if idx == 0:  # Only first one get connected to ethernet
            ethernet_hub.add_server(server)

        server.start()

    try:
        while(1):
            intr = input("ISR Num:")
            intr = int(intr)
            interrupter.trigger_interrupt(intr)

            pass
    except KeyboardInterrupt:
        pass
    log.info("Shutting Down")
    ethernet_hub.shutdown()
    wireless_hub.shutdown()
