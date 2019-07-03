# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a
# non-exclusive license for use of this work by or on behalf of the U.S.
# Government. Export of this data may require a license from the United States
# Government.
from os import path, system
from ..bp_handler import BPHandler, bp_handler
import IPython
import logging
log = logging.getLogger("Debugging")
log.setLevel(logging.DEBUG)

BFAR = 0xE000ED38
MMAR = 0xE000ED34


class DebugHelper():
    def __init__(self, qemu):
        self.qemu = qemu

    def get_mem(self, addr):
        return self.qemu.read_memory(addr, 4, 1)

    def parse_cfsr(self, cfsr, sp_offset):
        print("CFSR 0x%x" % cfsr)
        print("MemManage Flags")
        if cfsr & (1 << 7):
            print("\tMemManage Fault Address Valid: 0x%x" % self.get_mem(MMAR))
        if cfsr & (1 << 5):
            print(
                "\tMemManage fault occurred during floating-point lazy state preservation")
        if cfsr & (1 << 4):
            print(
                "\tStacking for an exception entry has caused one or more access violations")
        if cfsr & (1 << 3):
            print(
                "\tUnstacking for an exception return has caused one or more access violations")
        if cfsr & (1 << 1):
            print("\tData Access, Stacked PC 0x%x, Faulting Addr 0x%x" % (
                self.get_stacked_pc(sp_offset), self.get_mem(MMAR)))
        if cfsr & (1):
            print("\tInstruction Access Violation, Stacked PC 0x%x" %
                  (self.get_stacked_pc(sp_offset)))
        print("BusFault:")
        if cfsr & (1 << 15):
            print("\t Bus Fault Addr Valid 0x%x" % self.get_mem(BFAR))
        if cfsr & (1 << 13):
            print("\tbus fault occurred during")
        if cfsr & (1 << 12):
            print("\tException Stacking fault")
        if cfsr & (1 << 11):
            print("\tException UnStacking fault")
        if cfsr & (1 << 10):
            print("\tImprecise data bus error, may not have location")
        if cfsr & (1 << 9):
            print("\tPrecise data bus error, Faulting Addr: %0x" %
                  self.get_mem(BFAR))
        if cfsr & (1 << 8):
            print("\tInstruction bus error")

        print("Other Faults")
        if cfsr & (1 << (9+16)):
            print("\tDiv by zero, Stacked PC has Addr")
        if cfsr & (1 << (8+16)):
            print("\tUnaligned Fault Stacking fault")
        if cfsr & (1 << (3+16)):
            print("\tNo Coprocessor")
        if cfsr & (1 << (2+16)):
            print("\tInvalid PC load UsageFault, Stacked PC has Addr")
        if cfsr & (1 << (1+16)):
            print("\tInvalid state UsageFault, Stacked PC has Addr")
        if cfsr & (1 << (16)):
            print("\tUndefined instruction UsageFault, Stacked PC has Addr")

    def print_exception_stack(self, offset=0):
        '''
            Prints registers pushed on the stack by exception entry
        '''
        #  http://infocenter.arm.com/help/index.jsp?topic=/com.arm.doc.dui0553a/Babefdjc.html
        sp = self.qemu.regs.sp
        sp += offset
        print("Registers Stacked by Exception")
        print("R0: 0x%08x" % self.get_mem(sp))
        print("R1: 0x%08x" % self.get_mem(sp+4))
        print("R2: 0x%08x" % self.get_mem(sp+8))
        print("R3: 0x%08x" % self.get_mem(sp+12))
        print("R12: 0x%08x" % self.get_mem(sp+16))
        print("LR: 0x%08x" % self.get_mem(sp+20))
        print("PC: 0x%08x" % self.get_mem(sp+24))
        print("xPSR: 0x%08x" % self.get_mem(sp+28))
        # TODO Check CCR for floating point and print S0-S15 FPSCR

    def print_hardfault_info(self, stack_offset=0):
        '''
            Prints Hardfault info, alias for print_hardfault_info
        '''
        print("Configurable Fault Status Reg")
        hardfault_status = self.get_mem(0xE000ED2C)
        self.print_exception_stack(stack_offset)
        self.parse_hardfault(hardfault_status, stack_offset)

        cfsr = self.get_mem(0xE000ED28)
        self.parse_cfsr(cfsr, stack_offset)

    def hf(self, stack_offset=0):
        '''
            Prints Hardfault info, alias for print_hardfault_info
        '''
        self.print_hardfault_info(stack_offset)

    def get_stacked_pc(self, stackoffset=0):
        '''
            Gets the PC pushed on the stack from in an ISR
            Offset can be used adjust if additional things have been
            pushed to stack
        '''
        sp = self.qemu.regs.sp
        return self.get_mem(sp+(4*6)+stackoffset)

    def parse_hardfault(self, hardfault, sp_offset):
        print("Hard Fault 0x%x Reason: " % hardfault, end=' ')
        if hardfault & (1 << 30):
            print("Forced--Other fault elavated")
        if hardfault & (1 << 1):
            print("Bus Fault")
        print("Stacked PC 0x%x" % (self.get_stacked_pc(sp_offset)))


class IPythonShell(BPHandler):
    '''
        Returns an increasing value for each addresss accessed
    '''

    def __init__(self):
        self.addr2name = {}

    def register_handler(self, addr, func_name):
        self.addr2name[addr] = func_name
        return IPythonShell.get_value

    @bp_handler
    def get_value(self, qemu, addr):
        '''
            Gets the counter value
        '''

        log.warning("In Debug: %s" % self.addr2name[addr])
        qemu.write_bx_lr(qemu.regs.pc)
        intercept = False
        ret_val = None
        d = DebugHelper(qemu)
        system('stty sane')  # Make so display works
        IPython.embed()

        # return intercept, ret_val
        return False, ret_val
