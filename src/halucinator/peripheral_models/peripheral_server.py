# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.

import zmq
import yaml
from functools import wraps
from multiprocessing import Process
import logging
log = logging.getLogger("PeripheralServer")
log.setLevel(logging.DEBUG)

__rx_handlers__ = {}
__rx_context__ = zmq.Context()
__tx_context__ = zmq.Context()
__stop_server = False
__rx_socket__ = None
__tx_socket__ = None

__process = None
__qemu = None

output_directory = None
base_dir = None


def peripheral_model(cls):
    '''
        Decorator which registers classes as peripheral models 
    '''
    methods = [getattr(cls, x) for x in dir(
        cls) if hasattr(getattr(cls, x), 'is_rx_handler')]
    for m in methods:
        key = 'Peripheral.%s.%s' % (cls.__name__, m.__name__)
        log.info("Adding method: %s" % key)
        __rx_handlers__[key] = (cls, m)
        if __rx_socket__ != None:
            log.info("Subscribing to: %s" % key)
            __rx_socket__.setsockopt(zmq.SUBSCRIBE, key)

    return cls


def tx_msg(funct):
    '''
        This is a decorator that sends output of the wrapped function as 
        a tagged msg.  The tag is the class_name.func_name
    '''
    @wraps(funct)
    def tx_msg_decorator(model_cls, *args):
        '''
            Sends a message using the class.funct as topic
            data is a yaml encoded of the calling model_cls.funct
        '''
        global __tx_socket__
        data = funct(model_cls, *args)
        topic = "Peripheral.%s.%s" % (model_cls.__name__, funct.__name__)
        msg = encode_zmq_msg(topic, data)
        log.info("Sending: %s" % msg)
        __tx_socket__.send(msg)
    return tx_msg_decorator


def reg_rx_handler(funct):
    '''
        This is a decorator that registers a function to handle a specific
        type of message
    '''
    funct.is_rx_handler = True
    return funct


def encode_zmq_msg(topic, msg):
    data_yaml = yaml.safe_dump(msg)
    return "%s %s" % (topic, data_yaml)


def decode_zmq_msg(msg):
    topic, encoded_msg = msg.split(' ', 1)
    decoded_msg = yaml.safe_load(encoded_msg)
    return (topic, decoded_msg)


def start(rx_port=5555, tx_port=5556, qemu=None):
    # TODO Change from localhost if needed
    global __rx_socket__
    global __tx_socket__
    global __rx_context__
    global __tx_context__
    global __rx_handlers__
    global __process
    global __qemu
    global output_directory

    output_directory = qemu.avatar.output_directory
    __qemu = qemu
    log.info('Starting Peripheral Server, In port %i, outport %i' %
             (rx_port, tx_port))
    # Setup subscriber
    __rx_socket__ = __rx_context__.socket(zmq.SUB)

    __rx_socket__.connect("tcp://localhost:%i" % rx_port)

    for topic in list(__rx_handlers__.keys()):
        log.info("Subscribing to: %s" % topic)
        __rx_socket__.setsockopt(zmq.SUBSCRIBE, topic)

    # Setup Publisher
    __tx_socket__ = __tx_context__.socket(zmq.PUB)
    __tx_socket__.bind("tcp://*:%i" % tx_port)

    #__process = Process(target=run_server).start()


def trigger_interrupt(num):
    global __qemu
    log.info("Sending Interrupt: %s" % num)
    __qemu.trigger_interrupt(num)


def run_server():
    global __rx_handlers__
    global __rx_socket__
    global __stop_server
    global __qemu

    __stop_server = False
    __rx_socket__.setsockopt(zmq.SUBSCRIBE, '')

    poller = zmq.Poller()
    poller.register(__rx_socket__, zmq.POLLIN)
    while(not __stop_server):
        socks = dict(poller.poll(1000))
        if __rx_socket__ in socks and socks[__rx_socket__] == zmq.POLLIN:
            string = __rx_socket__.recv()
            topic, msg = decode_zmq_msg(string)
            log.info("Got message: Topic %s  Msg: %s" % (str(topic), str(msg)))

            if topic.startswith("Peripheral"):
                if topic in __rx_handlers__:
                    method_cls, method = __rx_handlers__[topic]
                    method(msg)
                else:
                    log.error(
                        "Unhandled peripheral message type received: %s" % topic)

            elif topic.startswith("Interrupt.Trigger"):
                log.info("Triggering Interrupt %s" % msg['num'])
                trigger_interrupt(msg['num'])
            elif topic.startswith("Interrupt.Base"):
                log.info("Setting Vector Base Addr %s" % msg['num'])
                __qemu.set_vector_table_base(msg['base'])
            else:
                log.error("Unhandled topic received: %s" % topic)
    log.info("Peripheral Server Shutdown Normally")


def stop(self):
    global __process
    global __stop_server
    __stop_server = True
    __process.join()
