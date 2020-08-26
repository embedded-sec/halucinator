# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.
from os import path, system
from ..bp_handler import BPHandler, bp_handler
from ..intercepts import register_bp_handler
import IPython
import logging
import avatar2
from ... import hal_config
log = logging.getLogger(__name__)
from ... import hal_log
hal_log = hal_log.getHalLogger()

class FunctionCaller():
    def __init__(self, qemu, start_addr, size, 
                 callee_addr, args, callee_fname=None):
        self.qemu = qemu
        self.args = args
        self.start_addr = start_addr
        self.size =  size
        self.callee_addr = callee_addr
        self.callee_fname = callee_fname
        self.return_addr = None # Subclass needs to set in init
        self.regs = {}

    def reg_size(self):
        return 4

    def save_state(self):
        for reg in sorted(self.qemu.avatar.arch.registers.keys()):
            log.debug("Saving Register: %s" % reg)
            self.regs[reg] = self.qemu.read_register(reg)

    def restore_state(self):
        try:
            for reg in sorted(self.qemu.avatar.arch.registers.keys()):
                log.debug("Restoring Register: %s" % reg)
                self.qemu.write_register(reg, self.regs[reg])
        except KeyError as e:
            log.error("Register key not available, likely restore called before save")
            raise(e)

    def _call(self):
        #Needs to over written by architecture specific call
        raise(NotImplementedError("Override with Arch Specific implementation"))

    def setup_stack_and_args(self):
        raise(NotImplementedError("Override with Arch Specific implementation"))

    def get_return_addr(self):
        return self.return_addr

    def call(self):
        self.save_state()
        self.setup_stack_and_args()
        self._call()

    def function_return(self):
        self.restore_state()

class ARMFunctionCaller(FunctionCaller):
    def __init__(self, qemu, start_addr, size, 
                 callee_addr, args, callee_fname=None):
        '''
            Setups ARM FunctionCaller with desending stack, memory looks like
            
            +-------------+ highest addr
            | return addr |
            + ------------+
            |    Stack    |
            |      |      |
            |      |      |
            |      V      |
            |             |
            +-------------+
        '''
        super().__init__(qemu, start_addr, size, callee_addr, args, callee_fname)

        #Uses decending stack so set sp to top of memory
        self.initial_sp = self.start_addr + size - self.reg_size()
        #TODO fix so multiple return break points can be used
        self.return_addr = self.start_addr + size & 0xFFFFFFFE 

    def setup_stack_and_args(self):
        for idx, arg in enumerate(self.args):
            if idx == 4:
                break
            self.qemu.write_register("r%i"% idx, arg)
            

        if len(self.args) > 4:
            raise (NotImplementedError("Stack parameters not supported yet"))

        self.qemu.regs.sp = self.initial_sp
    
    def _call(self):
        self.qemu.regs.lr = self.return_addr
        self.qemu.regs.pc = self.callee_addr 

class FunctionCallerIntercept():

    MEMORY_REGION_NAME = "halucinator_caller"

    def __init__(self):
        
        self.function_caller = {}
        self.interactive = {}

    def find_memory_region(self):
        '''
            Gets memory region used for stack and return addr
        '''
        for mem_interval in self.qemu.avatar.memory_ranges:
            m = mem_interval.data
            if m.name == self.MEMORY_REGION_NAME:
                if m.permissions != 'rwx':
                    raise(ValueError("Memory region %s must be 'rwx'"%
                                     self.MEMORY_REGION_NAME))
                return m.address, m.size
        raise(ValueError("Memory Region named: %s required by %s"%
                         (self.MEMORY_REGION_NAME, self.__class__)))

    def register_handler(self, qemu, addr, function, callee, args=None, 
                         interactive=False, 
                         stack_size=161984,
                         is_return=False,break_type="BP",watchpoint = ""):
        '''
        This will be called by the intercept registration function.
        **Note** only a single instance of the class is create, and this 
        function is called for each creation of an intercept in the halucinator
        config.  Thus, addr (of the breakpoint) is used as key to save
        associate values for given intercept.

        addr: address of the break point
        function: function name for address of break point
        callee: function or address to call
        args : List of parameters to provide function
        interactive: If true IPython shell will be launched after setting up
                     call and after return
        '''

        # The this function gets called twice, for each value entry in 
        # intercept config  file.  Once to register the bp that will cause
        # the function to be called, and again to register the bp that will 
        # catch the return
        if is_return: #If is return just register the handler
            return FunctionCallerIntercept.return_handler

        if args is None:
            args = []
        self.qemu = qemu
        self.memory_addr, self.memory_size = self.find_memory_region()
        self.next_stack_addr = self.memory_addr

        if self.qemu.avatar.arch != avatar2.archs.arm.ARM:
            raise(ValueError("Architecture (%s) not supported") %
                  (str(self.qemu.avatar.arch)))

        if type(callee) == str:
            try:
                callee_addr = self.qemu.avatar.callables[callee]
                callee_fname = callee
            except KeyError:
                log.error("Callee(%s) invalid for %s, 0x%08x, check intercept config" 
                          %(callee, function, addr))
                exit(-1)
        else:
            callee_fname = hex(callee)
            callee_addr = callee

        
        if self.qemu.avatar.arch == avatar2.archs.arm.ARM:
            stack_addr = self.get_stack_addr(stack_size)
            caller = ARMFunctionCaller(self.qemu, stack_addr, stack_size,
                                      callee_addr, args, callee_fname)
            return_addr = caller.get_return_addr()
            # Setup state to be used for both calll and return break points
            self.function_caller[addr] = caller
            self.function_caller[return_addr] = caller
            # Interactive set for both call and return
            self.interactive[addr] = interactive
            self.interactive[return_addr] = interactive
            # Set break point on return address that will execute function 
            # clean up
            if watchpoint == "":
                self.setup_return_bp(function, callee_addr, return_addr)
            else:
                self.setup_return_bp(function, callee_addr, return_addr,break_type="WP",rw=watchpoint)


        return FunctionCallerIntercept.initiate_call_handler

    def get_stack_addr(self, size):
        if self.next_stack_addr:
            stack_addr = self.next_stack_addr
            self.next_stack_addr += size
            if self.next_stack_addr >= (self.memory_addr + self.memory_size):
                self.next_stack_addr = None
            return stack_addr
        raise(ValueError("Insufficient Memory for stacks " +\
                          "increase size of %s memory regions" % 
                          FunctionCallerIntercept.MEMORY_REGION_NAME))
            

    def setup_return_bp(self, function, callee_addr, return_addr, break_type="BP",rw="r"):
        if break_type == "WP":
            config = {'cls': '.'.join([self.__class__.__module__, self.__class__.__name__]),
                    'registration_args': 
                        {'callee': callee_addr, 'is_return': True},
                    'run_once': True,
                    'function': function +'-return', 'addr': return_addr, 'watchpoint': rw}
        else:
            config = {'cls': '.'.join([self.__class__.__module__, self.__class__.__name__]),
                    'registration_args': 
                        {'callee': callee_addr, 'is_return': True},
                    'run_once': True,
                    'function': function +'-return', 'addr': return_addr}

        intercept_config = hal_config.HalInterceptConfig(__file__, **config)
        register_bp_handler(self.qemu, intercept_config)
        return

    @bp_handler
    def initiate_call_handler(self, qemu, addr):
        '''
            Perform the function call
        '''
        caller = self.function_caller[addr]
        caller.call()
        if self.interactive[addr]:
            hal_log.info("Before call of %s" % caller.callee_fname)
            IPython.embed()
        return False, None # Don't change PC, or R0

    @bp_handler
    def return_handler(self, qemu, addr):
        '''
            Preform function clean up
        '''
        caller = self.function_caller[addr]
        if self.interactive[addr]:
            hal_log.info("After call of %s" % caller.callee_fname)
            IPython.embed()
        
        caller.restore_state()

        return False, None

    