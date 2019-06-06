# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC 
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a 
# non-exclusive license for use of this work by or on behalf of the U.S. 
# Government. Export of this data may require a license from the United States 
# Government.

from os import sys, path

from ..peripheral_models.peripheral_server import encode_zmq_msg, decode_zmq_msg
from ioserver import IOServer
import zmq
import time


class SendInterrupt(object):
    def __init__(self, ioserver):
        self.ioserver = ioserver

    def trigger_interrupt(self, interrupt_number, walk=1):
        topic = "Interrupt.Trigger"   
        for x in range(interrupt_number, interrupt_number + walk):
            data = {'num':x}
            self.ioserver.send_msg(topic, data)
            
    def set_vector_base(self, base_addr):
        topic = "Interrupt.Base"
        data = {'base':base_addr}
        self.ioserver.send_msg(topic, data)


if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('-i', '--interrupt', type=int, 
                   help='Interrupt number to trigger')
    p.add_argument('-b', '--base_addr',
                   help='Base Address to set vector table to')
    p.add_argument('-r', '--rx_port', default=5556,
                   help='Port number to receive zmq messages for IO on')
    p.add_argument('-t', '--tx_port', default=5555, type=int,
                   help='Port number to send IO messages via zmq')
    p.add_argument('-w', '--walk', default=1, type=int,
                   help='Walk x number of interrupts starting from -i')
    args = p.parse_args()


    if args.interrupt is None and args.base_addr is None:
        print "Either -i or -b required"
        print p.usage()

    io_server = IOServer(args.rx_port, args.tx_port)
    interrupter = SendInterrupt(io_server)
    time.sleep(1)
    if args.interrupt is not None:
        interrupter.trigger_interrupt(args.interrupt, args.walk)
    
    if args.base_addr is not None:
        if args.base_addr.startswith("0x"):
            base = int(args.base_addr, 16)
        else:
            base = int(args.base_addr)
        interrupter.set_vector_base(base)
    