# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC 
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a 
# non-exclusive license for use of this work by or on behalf of the U.S. 
# Government. Export of this data may require a license from the United States 
# Government.
from ...peripheral_models.interrupts import Interrupts
from ...peripheral_models.timer_model import TimerModel
from avatar2.peripherals.avatar_peripheral import AvatarPeripheral
from ..intercepts import tx_map, rx_map
from ..bp_handler import BPHandler, bp_handler
import time
from collections import defaultdict

import logging
log = logging.getLogger("Timers")
# log.setLevel(logging.DEBUG)

class Timers(BPHandler, AvatarPeripheral):

    def __init__(self, model=TimerModel):
        self.model = model
        self.org_lr = None
        self.current_channel = 0
        self.name2isr_lut = {'Timer0': 0x20, 'Timer1':0x21, 'Timer3': 0x22, 'Timer4': 0x23, 'Timer5': 0x24}
        self.irq_rates ={}
        self.name = 'Timer'
        self._init_mmio()

    def _init_mmio(self):
        #TODO should really have 5 instances of the AvatarPeripherals one for
        # each timer
        self.address = 0x42002000
        self.size = 0x2000

        log.info("Setting Handlers" )
        AvatarPeripheral.__init__(self, self.name, self.address, self.size)
        self.read_handler[0:self.size] = self.hw_read 
        self.write_handler[0:self.size] = self.hw_write

    def get_mmio_info(self):
        return self.name, self.address, self.size, 'rw-'

    def hw_read(self, offset, size, pc):       
        value = 0
        
        if offset == 0x0c0e:  #TC3 INT Reg
            value = 0xff

        log.info("Read from addr: 0x%08x, offset:0x%04x size: %i value: 0x%0x, pc: %s" %(self.address + offset, offset, size, value, hex(pc)))
        return value
        
    def hw_write(self, offset, size, value, pc):
        log.info("Write to addr, 0x%08x size: %i value: 0x%0x, pc: %s" %(self.address + offset, size, value, hex(pc)))  
        return True         

    def register_handler(self, addr, func_name, irq_rates=None):
        '''
            irq_rate(dict): {Name: rate (in seconds)}
        '''
        if irq_rates is not None:
            self.irq_rates = irq_rates
        return BPHandler.register_handler(self, addr, func_name)
    
    @bp_handler(['tc_init'])
    def enable(self, qemu, bp_addr):
        log.info("Initializing %s, %s" %(hex(qemu.regs.r0), hex(qemu.regs.r1)))
        for irq_name, irq_rate in self.irq_rates.items():
            self.model.start_timer(irq_name, self.name2isr_lut[irq_name], irq_rate)
        return False, None  # Just let it run 


    @bp_handler(['_tc_interrupt_handler'])
    def isr_handler(self, qemu, bp_addr):
        idx = qemu.regs.r0
        tc_instances_ptr = 0x000024E0
        tc_instances = 0x200021AC
        tc_instance = qemu.read_memory(tc_instances + (idx * 4), 4)
        hw_addr = qemu.read_memory(tc_instance, 4, 1)

        log.info("_TC_Handler: pc: 0x%08x,  idx: 0x%08x, tc_instances_ptr: 0x%08x, TC_instance: 0x%08x" %
                (qemu.regs.pc, idx, qemu.read_memory(tc_instances_ptr, 4, 1), tc_instance))
        log.info("HW_Addr:  0x%08x  r4 0x%08x" %(hw_addr, qemu.regs.r4))
        import os; os.system("stty sane")
        import IPython; IPython.embed()
        return False, None  # Just let it run 
    
    def disable(self, irq_name):
        self.model.stop_timer(irq_name)
        

   


