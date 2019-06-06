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

log = logging.getLogger("STM32F4_TIM")
log.setLevel(logging.INFO)


class STM32_TIM(BPHandler):

    def __init__(self, model=TimerModel):
        self.model = model
        self.org_lr = None
        self.current_channel = 0
        self.addr2isr_lut = {
            #'0x40000200': 0x32
            0x40000400: 45
        }
        self.irq_rates = {}
        self.name = 'STM32_TIM'

    @bp_handler(['HAL_TIM_Base_Init'])
    def tim_init(self, qemu, bp_addr):
        tim_obj = qemu.regs.r0
        tim_base = qemu.read_memory(tim_obj, 4, 1)

        log.info("STM32_TIM init, base: %#08x" % (tim_base))
        #self.model.start_timer(hex(tim_base), self.name2isr_lut[irq_name], irq_rate)
        # TODO: HACK: FIXME: Take this out when we have better NVIC handling.
        # We call into the MSP init function to get it to set up our IRQ prio
        # without knowing what's there, it changes with #defines
        #qemu.regs.pc = qemu.avatar.callables['HAL_TIM_Base_MspInit']
        #import ipdb; ipdb.set_trace()
        return False, None

    @bp_handler(['HAL_TIM_Base_DeInit'])
    def deinit(self, qemu, bp_addr):
        tim_obj = qemu.regs.r0
        tim_base = qemu.read_memory(tim_obj, 4, 1)

        log.info("STM32_TIM deinit, base: %#08x" % (hex(tim_base)))
        # self.model.start_timer(hex(tim_base), self.name2isr_lut[irq_name], irq_rate)
        return True, 0

    @bp_handler(['HAL_TIM_ConfigClockSource'])
    def config(self, qemu, bp_addr):
        tim_obj = qemu.regs.r0
        tim_base = qemu.read_memory(tim_obj, 4, 1)

        log.info("STM32_TIM config, base: %#08x" % (hex(tim_base)))
        # self.model.start_timer(hex(tim_base), self.name2isr_lut[irq_name], irq_rate)
        return True, 0

    @bp_handler(['HAL_TIMEx_MasterConfigSynchronization'])
    def sync(self, qemu, bp_addr):
        tim_obj = qemu.regs.r0
        tim_base = qemu.read_memory(tim_obj, 4, 1)
        log.info("STM32_TIM sync, base: %#08x" % (hex(tim_base)))
        # self.model.start_timer(hex(tim_base), self.name2isr_lut[irq_name], irq_rate)
        return True, 0

    @bp_handler(['HAL_TIM_Base_Start_IT'])
    def start(self, qemu, bp_addr):
        tim_obj = qemu.regs.r0
        tim_base = qemu.read_memory(tim_obj, 4, 1)

        log.info("STM32_TIM start, base: %#08x" % tim_base)
        self.model.start_timer(hex(tim_base), self.addr2isr_lut[tim_base], 2)
        return True, None  # Just let it run

    @bp_handler(['HAL_TIM_IRQHandler'])
    def isr_handler(self, qemu, bp_addr):
        tim_obj = qemu.regs.r0
        tim_base = qemu.read_memory(tim_obj, 4, 1)
        log.info("TICK: Timer %#08x" % tim_base)
        # Call HAL_TIM_PeriodElapsedCallback
        # TODO: Tims can do other things besides elapse.
        # When we see a tim doing that, put it here
        # Leave the regs unchanged, as they should be correct.
        qemu.regs.pc = qemu.avatar.callables['HAL_TIM_PeriodElapsedCallback']
        return False, None

    @bp_handler(['HAL_TIM_Base_Stop_IT'])
    def stop(self, qemu, bp_addr):
        tim_obj = qemu.regs.r0
        tim_base = qemu.read_memory(tim_obj, 4, 1)
        self.model.stop_timer(hex(tim_base))
        return True, 0

    @bp_handler(['HAL_Delay'])
    def sleep(self, qemu, bp_handler):
        amt = qemu.regs.r0 / 1000.0
        log.debug("sleeping for %f" % amt)
        #time.sleep(amt)
        return True, 0

    @bp_handler(['HAL_SYSTICK_Config'])
    def systick_config(self, qemu, bp_addr):
        #rate = qemu.regs.r0
        rate = 5
        systick_irq = 15
        log.info("Setting SysTick rate to %#08x" % rate)
        self.model.start_timer('SysTick', systick_irq, rate)
        return True, 0

