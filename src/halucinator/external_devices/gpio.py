# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC 
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a 
# non-exclusive license for use of this work by or on behalf of the U.S. 
# Government. Export of this data may require a license from the United States 
# Government.

from os import sys, path
import zmq
from  multiprocessing import Process
import os
import time
from ..peripheral_models.peripheral_server import encode_zmq_msg, decode_zmq_msg


__run_server = True
def rx_from_emulator(emu_rx_port):
    ''' 
        Receives 0mq messages from emu_rx_port    
        args:
            emu_rx_port:  The port number on which to listen for messages from
                          the emulated software
    '''
    global __run_server
    context = zmq.Context()
    mq_socket = context.socket(zmq.SUB)
    mq_socket.connect("tcp://localhost:%s"%emu_rx_port)
    #mq_socket.setsockopt(zmq.SUBSCRIBE, "GPIO.write_pin")
    mq_socket.setsockopt(zmq.SUBSCRIBE,'')
    #mq_socket.setsockopt(zmq.SUBSCRIBE, "GPIO.toggle_pin")
  
    print "Setup GPIO Listener"
    while (__run_server):
        msg = mq_socket.recv()
        print "Got from emulator:", msg
        topic, data = decode_zmq_msg(msg)
        print "Pin: ", data['id'],"Value", data['value']

def update_gpio(emu_tx_port):
    global __run_server
    global __host_socket
    topic = "Peripheral.GPIO.ext_pin_change"
    context = zmq.Context()
    to_emu_socket = context.socket(zmq.PUB)
    to_emu_socket.bind("tcp://*:%s"%emu_tx_port)
    
    try:
        while (1):
            time.sleep(2)
            #Prompt for pin and value
            #pin = raw_input("Pin: ")
            #value = raw_input("Value: ")
            #data = {'id':pin, 'value':int(value)}
            #msg = encode_zmq_msg(topic, data)
            #to_emu_socket.send(msg)
    except KeyboardInterrupt:
        __run_server = False


def start(interface, emu_rx_port=5556, emu_tx_port=5555):
    global __run_server
    #print  "Host socket setup"
    emu_rx_process = Process(target=rx_from_emulator, args=(emu_rx_port,)).start()
    update_gpio(emu_tx_port)
    emu_rx_process.join()
    


if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('-r', '--rx_port', default=5556,
                   help='Port number to receive zmq messages for IO on')
    p.add_argument('-t', '--tx_port', default=5555,
                   help='Port number to send IO messages via zmq')
    args = p.parse_args()
    start(args.rx_port, args.tx_port)