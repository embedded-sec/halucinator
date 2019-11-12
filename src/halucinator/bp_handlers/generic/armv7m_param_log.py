# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.

from ..bp_handler import BPHandler, bp_handler
import re
from binascii import hexlify
from os import path
import sys

sys.path.insert(0, path.dirname(path.dirname(path.abspath(__file__))))


class ARMv7MEABILogger(BPHandler):
    '''
        Logs parameters to standard out or input file


        [r0, r1, r2, r3, s0#4, s4#4, s8#4]
    '''

    def __init__(self, filename=None):
        self.fd = None
        if filename != None:
            self.fd = open(filename, 'wt')
        self.params = {}
        self.ret_values = {}
        self.func_names = {}

    def register_handler(self, addr, func_name, params=None, ret_val=None):
        '''
        This will be called by the intercept registration function

        args:
            func_name: Name of function being bp will execute for
            params: Specifies where parameters are stored format
                    [r0, r1, r2, r3, s0#4, s4#4, s8#4] 
                    (r0 is register number, and s0#4 is stack<offset>#<size>)
        '''
        if params == None:
            params = []
        self.func_names[addr] = func_name
        self.params[addr] = params
        self.ret_values[addr] = ret_val
        return ARMv7MEABILogger.log_bp_and_params

    @bp_handler  # bp_handler no args, can intercept any function
    def log_bp_and_params(self, qemu, addr):
        '''

        '''
        func_name = self.func_names[addr]
        params = self.params[addr]
        print(params)
        sp = qemu.regs.sp
        param_values = []
        for p_num, param in enumerate(params):
            if param.startswith('r'):
                print("Loc", param)
                value = qemu.read_register(param)
            elif param.startswith('s'):
                m = re.match('s([0-9]+)#([0-9]+)', param)
                if m != None:
                    (offset, length) = m.groups()
                    offset = int(offset)
                    length = int(length)
                    value = qemu.read_memory(sp+offset, 1, length, raw=True)
                    value = hexlify(value)
            if value != None:
                if type(value) == int:
                    param_values.append("%s: 0x%08x" % (p_num, value))
                else:
                    param_values.append("%s: %s" % (p_num, str(value)))
        pc = qemu.regs.pc
        log_str = hex(pc) + ": " + func_name + " " + \
            ", ".join(param_values) + "\n"
        if self.fd:
            self.fd.write(log_str)
            self.fd.flush()
        else:
            print(log_str)

        return True, self.ret_values[addr]
