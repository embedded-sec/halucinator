# Copyright 2020 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.


from avatar2 import Avatar, QemuTarget

class ARMQemuTarget(QemuTarget):
    '''
        Implements a QEMU target that has function args for use with
        halucinator.  Enables read/writing and returning from
        functions in a calling convention aware manner
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_arg(self, idx):
        '''
            Gets the value for a function argument (zero indexed)

            :param idx  The argument index to return
            :returns    Argument value
        '''
        if idx >= 0 and idx < 4:
            return self.read_register("r%i" % idx)
        elif idx >= 4:
            sp = self.read_register("sp")
            stack_addr = sp + (idx-4) * 4
            return self.read_memory(stack_addr, 4, 1)
        else:
            raise ValueError("Invalid arg index")

    def set_arg(self, idx, value):
        '''
            Sets the value for a function argument (zero indexed)


            :param idx      The argument index to return
            :param value    Value to set index to 
        '''
        if idx >= 0 and idx < 4:
            self.write_register("r%i" % idx, value)
        elif idx >= 4:
            sp = self.read_register("sp")
            stack_addr = sp + (idx-4) * 4
            self.write_memory(stack_addr, 4, value)
        else:
            raise ValueError(idx)

    def get_ret_addr(self):
        '''
            Gets the return address for the function call

            :returns Return address of the function call
        '''
        return self.regs.lr

    def set_ret_addr(self, ret_addr):
        '''
            Sets the return address for the function call
            :param ret_addr Value for return address
        '''
        self.regs.lr = ret_addr

    def execute_return(self, ret_value):
        if ret_value != None:
            # Puts ret value in r0
            self.regs.r0 = ret_value
        self.regs.pc = self.regs.lr


    

    def irq_set(self, irq_num=1, cpu=0):
        self.protocols.monitor.execute_command("avatar-set-irq", 
            args={"cpu_num":cpu, "irq_num": irq_num, "value":1})

    def irq_clear(self, irq_num=1, cpu=0):
        self.protocols.monitor.execute_command("avatar-set-irq", 
            args={"cpu_num":cpu, "irq_num": irq_num, "value":0})

    def irq_pulse(self, irq_num=1, cpu=0):
        self.protocols.monitor.execute_command("avatar-set-irq", 
            args={"cpu_num":cpu, "irq_num": irq_num, "value":3})


    def get_symbol_name(self, addr):
        """
        Get the symbol for an address

        :param addr:    The name of a symbol whose address is wanted
        :returns:         (Symbol name on success else None
        """

        return self.avatar.config.get_symbol_name(addr)