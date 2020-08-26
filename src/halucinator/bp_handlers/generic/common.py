from ..bp_handler import BPHandler, bp_handler
import logging
from ... import hal_log

log = logging.getLogger(__name__)
hal_log = hal_log.getHalLogger()

class ReturnZero(BPHandler):
    '''
        Break point handler that just returns zero

        Halucinator configuration usage:
        - class: halucinator.bp_handlers.ReturnZero
          function: <func_name> (Can be anything)
          registration_args: {silent:false}
          addr: <addr>
    '''
    def __init__(self, filename=None):
        self.silent = {}
        self.func_names = {}

    def register_handler(self, qemu, addr, func_name, silent=False):
        self.silent[addr] = silent
        self.func_names[addr] = func_name
        return ReturnZero.return_zero

    @bp_handler
    def return_zero(self, qemu, addr):
        '''
            Intercept Execution and return 0
        '''
        if not self.silent[addr]:
            hal_log.info("ReturnZero: %s " %(self.func_names[addr]))
        return True, 0


class ReturnConstant(BPHandler):
    '''
        Break point handler that returns a constant

        Halucinator configuration usage:
        - class: halucinator.bp_handlers.ReturnConstant
          function: <func_name> (Can be anything)
          registration_args: { ret_value:(value), silent:false}
          addr: <addr>
    '''
    def __init__(self, filename=None):
        self.ret_values = {}
        self.silent = {}
        self.func_names = {}

    def register_handler(self, qemu, addr, func_name, ret_value=None, silent=False):
        self.ret_values[addr] = ret_value
        self.silent[addr] = ret_value
        self.func_names[addr] = func_name
        return ReturnConstant.return_constant

    @bp_handler
    def return_constant(self, qemu, addr):
        '''
            Intercept Execution and return 0
        '''
        if not self.silent[addr]:
            hal_log.info("ReturnConstant: %s : %#x" %(self.func_names[addr], self.ret_values[addr]))
        return True, self.ret_values[addr]


class SkipFunc(BPHandler):
    '''
        Break point handler that immediately returns from the function

        Halucinator configuration usage:
        - class: halucinator.bp_handlers.SkipFunc
          function: <func_name> (Can be anything)
          registration_args: {silent:false}
          addr: <addr>
    '''
    def __init__(self, filename=None):
        self.silent = {}
        self.func_names = {}

    def register_handler(self, qemu, addr, func_name, silent=False):
        self.silent[addr] = silent
        self.func_names[addr] = func_name
        return SkipFunc.skip

    @bp_handler
    def skip(self, qemu, addr):
        '''
            Just return
        '''
        if not self.silent[addr]:
            hal_log.info("SkipFunc: %s " %(self.func_names[addr]))
        return True, None