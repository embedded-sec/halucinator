# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. 
# Government retains certain rights in this software.

from os import sys, path
from ..peripheral_models.peripheral_server import encode_zmq_msg, decode_zmq_msg
import zmq
from  multiprocessing import Process
import os
import socket
import time
import binascii
import scapy.all as scapy

__run_server = True
__host_socket = None

def rx_from_emulator(emu_rx_port, interface):
    ''' 
        Receives 0mq messages from emu_rx_port    
        args:
            emu_rx_port:  The port number on which to listen for messages from
                          the emulated software
    '''
    global __run_server
    #global __host_socket
    topic = "Peripheral.EthernetModel.tx_frame"
    context = zmq.Context()
    mq_socket = context.socket(zmq.SUB)
    mq_socket.connect("tcp://localhost:%s"%emu_rx_port)
    mq_socket.setsockopt(zmq.SUBSCRIBE, topic)
  
    while (__run_server):
        msg = mq_socket.recv()
        #print "Got from emulator:", msg
        topic, data = decode_zmq_msg(msg)
        frame = data['frame']
        #if len(frame) < 64:
        #    frame = frame +('\x00' * (64-len(frame)))
        p = scapy.Raw(frame)
        scapy.sendp(p, iface=interface)
        #__host_socket.send(frame)
        print "Sending Frame (%i) on eth: %s" %(len(frame), binascii.hexlify(frame))


def rx_from_host(emu_tx_port, msg_id):
    global __run_server
    global __host_socket
    topic = "Peripheral.EthernetModel.rx_frame"
    context = zmq.Context()
    to_emu_socket = context.socket(zmq.PUB)
    to_emu_socket.bind("tcp://*:%s"%emu_tx_port)
    
    while (__run_server):
        pass
        # Listen for frame from host
        frame = __host_socket.recv(2048)
        data = {'interface_id':msg_id, 'frame':frame}
        msg = encode_zmq_msg(topic, data)
        to_emu_socket.send(msg)
        print "Sent message to emulator ", binascii.hexlify(frame)


def start(interface, emu_rx_port=5556, emu_tx_port=5555, msg_id=1073905664):
    global __run_server
    global __host_socket
    # Open socket to send raw frames on ethernet adapter
    os.system('ip link set %s promisc on' % interface) #Set to permisucous
    # os.system('ethtool -K %s tx off' % interface)

    ETH_P_ALL = 3
    __host_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
    __host_socket.bind((interface, 0))

    print  "Starting Servers"
    emu_rx_process = Process(target=rx_from_emulator, args=(emu_rx_port,interface)).start()
    emu_tx_process = Process(target=rx_from_host, args=(emu_tx_port,msg_id)).start()
    try:
        while (1):
            time.sleep(0.1)
    except KeyboardInterrupt:
        __run_server = False
    emu_rx_process.join()
    emu_tx_process.join()


if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('-r', '--rx_port', default=5556,
                   help='Port number to receive zmq messages for IO on')
    p.add_argument('-t', '--tx_port', default=5555,
                   help='Port number to send IO messages via zmq')
    p.add_argument('-i', '--interface', required=True,
                   help='Ethernet Interace to listen to')
    p.add_argument('--id', default=1073905664,
                   help='Ethernet Interace to listen to')
    args = p.parse_args()
    start(args.interface, args.rx_port, args.tx_port, args.id)