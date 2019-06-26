# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. 
# Government retains certain rights in this software.

from functools import wraps
from . import bp_handler as bp_handler
import importlib
import yaml
from ..util import hexyaml
import os
import logging
from .. import hal_stats as hal_stats
log = logging.getLogger("Intercepts")
log.setLevel(logging.DEBUG)


hal_stats.stats['used_intercepts'] = set()

def tx_map(per_model_funct):
    '''
        Decorator that maps this function to the peripheral model that supports
        it. It registers the intercept and calls the
        Usage:  @intercept_tx_map(<PeripheralModel.method>, ['Funct1', 'Funct2'])

        Args:
            per_model_funct(PeripheralModel.method):  Method of child class that
                this method is providing a mapping for
    '''
    print "In: intercept_tx_map", per_model_funct  
    def intercept_decorator(func):
        print "In: intercept_decorator", func
        @wraps(func)
        def intercept_wrapper(self, qemu, bp_addr):
            bypass, ret_value, msg = func(self, qemu, bp_addr)
            log.debug("Values:", msg)
            per_model_funct(*msg)
            return bypass, ret_value
        return intercept_wrapper
    return intercept_decorator


def rx_map(per_model_funct):
    '''
        Decorator that maps this function to the peripheral model that supports
        it. It registers the intercept and calls the
        Usage:  @intercept_rx_map(<PeripheralModel.method>, ['Funct1', 'Funct2'])

        Args:
            per_model_funct(PeripheralModel.method):  Method of child class that
                this method is providing a mapping for
    '''
    print "In: intercept_rx_map", per_model_funct 
    def intercept_decorator(func):
        print "In: intercept_decorator", func
        @wraps(func)
        def intercept_wrapper(self, qemu, bp_addr):
            models_inputs = per_model_funct()
            return func(self, qemu, bp_addr, *models_inputs)
        return intercept_wrapper
    return intercept_decorator


def bp_return(qemu, bypass, ret_value):
    '''
        Handles returning from breakpoint for ARMv7-M devices
        Args:
            bypass(bool):  If true bypasses execution of the function
            ret_value(bool): The return value to provide for the execution
    '''
    print "Intercept Return: ", (bypass, ret_value)
    return
    if ret_value != None:
        # Puts ret value in r0
        qemu.regs.r0 = ret_value
    if bypass:
        # Returns from function, by putting LR in PC
        qemu.regs.pc = qemu.regs.lr
        #log.info("Executing BX LR")
        #qemu.exec_bxlr()


initalized_classes = {}
bp2handler_lut = {}


def get_bp_handler(intercept_desc):
    '''
        gets the bp_handler class from the config file class name.
        Instantiates it if has not been instantiated before if 
        has it just returns the instantiated instance
    '''
    split_str = intercept_desc['class'].split('.')

    module_str = ".".join(split_str[:-1])
    class_str = split_str[-1]
    module = importlib.import_module(module_str)
    
    cls_obj = getattr(module, class_str)
    if cls_obj in  initalized_classes:
        bp_class = initalized_classes[cls_obj]
    else:
        if 'class_args' in intercept_desc and intercept_desc['class_args'] != None:
            print 'Class:' , cls_obj
            print 'Class Args:' , intercept_desc['class_args']
            bp_class = cls_obj( **intercept_desc['class_args'])
        else:
            bp_class = cls_obj()
        initalized_classes[cls_obj] = bp_class
    return bp_class


def register_bp_handler(qemu, intercept_desc):
    '''
    '''

    bp_cls = get_bp_handler(intercept_desc)
    if isinstance(intercept_desc['addr'], int):
        intercept_desc['addr'] = intercept_desc['addr'] & 0xFFFFFFFE #Clear thumb bit
    if 'registration_args' in intercept_desc and \
       intercept_desc['registration_args'] != None:
        handler = bp_cls.register_handler(intercept_desc['addr'], 
                                intercept_desc['function'], 
                                **intercept_desc['registration_args'])
    else:
        handler = bp_cls.register_handler(intercept_desc['addr'], 
                                intercept_desc['function'])
    log.info("Registering BP Handler: %s.%s : %s"%(intercept_desc['class'],intercept_desc['function'], hex(intercept_desc['addr'] )))
    bp = qemu.set_breakpoint(intercept_desc['addr'])
    hal_stats.stats[bp] = dict(intercept_desc)
    hal_stats.stats[bp]['count'] = 0
    hal_stats.stats[bp]['method'] = handler.__name__
    
    bp2handler_lut[bp] = (bp_cls, handler)


def interceptor(avatar, message):
    '''
        Callback for Avatar2 break point watchman.  It then dispatches to
        correct handler
    '''
    bp = int(message.breakpoint_number)
    qemu = message.origin
    pc = qemu.regs.pc & 0xFFFFFFFE #Clear Thumb bit

   
    cls, method = bp2handler_lut[bp]
    hal_stats.stats[bp]['count'] += 1
    hal_stats.write_on_update('used_intercepts', hal_stats.stats[bp]['function'])
    
    #print method
    try:
        intercept, ret_value = method(cls, qemu, pc)
    except:
        log.exception("Error executing handler %s" % (repr(method)))
        raise
    if intercept:
        if ret_value != None:
             # Puts ret value in r0
             qemu.regs.r0 = ret_value
        qemu.regs.pc = qemu.regs.lr
        #qemu.exec_return(ret_value)
    qemu.cont()
