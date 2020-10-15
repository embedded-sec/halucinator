# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.

from functools import wraps
from . import bp_handler as bp_handler
import importlib
import yaml
from ..util import hexyaml
import os
import logging
from .. import hal_stats as hal_stats
log = logging.getLogger(__name__)

from .. import hal_log as hal_log_conf
hal_log = hal_log_conf.getHalLogger()



hal_stats.stats['used_intercepts'] = set()
hal_stats.stats['bypassed_funcs'] = set()


def tx_map(per_model_funct):
    '''
        Decorator that maps this function to the peripheral model that supports
        it. It registers the intercept and calls the
        Usage:  @intercept_tx_map(<PeripheralModel.method>, ['Funct1', 'Funct2'])

        Args:
            per_model_funct(PeripheralModel.method):  Method of child class that
                this method is providing a mapping for
    '''
    print("In: intercept_tx_map", per_model_funct)

    def intercept_decorator(func):
        print("In: intercept_decorator", func)
        @wraps(func)
        def intercept_wrapper(self, target, bp_addr):
            bypass, ret_value, msg = func(self, target, bp_addr)
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
    print("In: intercept_rx_map", per_model_funct)

    def intercept_decorator(func):
        print("In: intercept_decorator", func)
        @wraps(func)
        def intercept_wrapper(self, target, bp_addr):
            models_inputs = per_model_funct()
            return func(self, target, bp_addr, *models_inputs)
        return intercept_wrapper
    return intercept_decorator

initalized_classes = {}
bp2handler_lut = {}

def get_bp_handler(intercept):
    '''
        gets the bp_handler class from the config file class name.
        Instantiates it if has not been instantiated before if 
        has it just returns the instantiated instance

        :param intercept: HALInterceptConfig
    '''
    split_str = intercept.cls.split('.')

    module_str = ".".join(split_str[:-1])
    class_str = split_str[-1]
    module = importlib.import_module(module_str)

    cls_obj = getattr(module, class_str)
    if cls_obj in initalized_classes:
        bp_class = initalized_classes[cls_obj]
    else:
        if intercept.class_args != None:
            log.info('Class: %s' % cls_obj)
            log.info('Class Args: %s' % intercept.class_args)
            bp_class = cls_obj(**intercept.class_args)
        else:
            bp_class = cls_obj()
        initalized_classes[cls_obj] = bp_class
    return bp_class


def register_bp_handler(qemu, intercept):
    '''
        Registers a BP handler for specific address

        :param qemu:    Avatar qemu target
        :param intercept: HALInterceptConfig
    '''
    if intercept.bp_addr is None:
        log.debug("No address specified for %s ignoring intercept" % intercept)
        return
    bp_cls = get_bp_handler(intercept)

    try:
        if intercept.registration_args != None:
            log.info("Registering BP Handler: %s.%s : %s, registration_args: %s" % (
                intercept.cls, intercept.function, hex(intercept.bp_addr),
                str(intercept.registration_args)))
            handler = bp_cls.register_handler(qemu,
                                            intercept.bp_addr,
                                            intercept.function,
                                            **intercept.registration_args)
        else:
            log.info("Registering BP Handler: %s.%s : %s" % (
                intercept.cls, intercept.function, hex(intercept.bp_addr)))
            handler = bp_cls.register_handler(qemu,
                                            intercept.bp_addr,
                                            intercept.function)
    except ValueError as e:
        hal_log.error("Invalid BP registration failed for %s" %(intercept))
        hal_log.error("Input registration args are %s" %(intercept.registration_args))
        exit(-1)

    if intercept.run_once:
        bp_temp = True
        log.debug("Setting as Tempory")
    else:
        bp_temp = False
        
    if intercept.watchpoint:
        if intercept.watchpoint == "r":
             bp = qemu.set_watchpoint(intercept.bp_addr, write=False, read=True)
        elif intercept_desc['watchpoint'] == "w":
            bp = qemu.set_watchpoint(intercept.bp_addr, write=True, read=False)
            
        else:
            bp = qemu.set_watchpoint(intercept.bp_addr, write=True, read=True)

    else:
        bp = qemu.set_breakpoint(intercept.bp_addr, temporary=bp_temp)


    hal_stats.stats[bp] = {'function': intercept.function, 
                           'desc': str(intercept), 
                           'count': 0, 
                           'method': handler.__name__}

    bp2handler_lut[bp] = (bp_cls, handler)
    log.info("BP is %i" % bp)


def interceptor(avatar, message):
    '''
        Callback for Avatar2 break point watchman.  It then dispatches to
        correct handler
    '''
    #HERE
    if message.__class__.__name__ == "WatchpointHitMessage":
        bp = int(message.watchpoint_number)
    else:
        bp = int(message.breakpoint_number)
    target = message.origin
    pc = target.regs.pc & 0xFFFFFFFE  # Clear Thumb bit


    cls, method = bp2handler_lut[bp]
    hal_stats.stats[bp]['count'] += 1
    hal_stats.write_on_update(
        'used_intercepts', hal_stats.stats[bp]['function'])

    # print method
    try:
        intercept, ret_value = method(cls, target, pc)
        if intercept:
            hal_stats.write_on_update('bypassed_funcs', hal_stats.stats[bp]['function'])
    except:
        log.exception("Error executing handler %s" % (repr(method)))
        raise
    if intercept:
        target.execute_return(ret_value)
    target.cont()
