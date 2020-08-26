# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.

from ...peripheral_models.interrupts import Interrupts
from ...peripheral_models.timer_model import TimerModel
from avatar2.peripherals.avatar_peripheral import AvatarPeripheral
from ..intercepts import tx_map, rx_map
from ..bp_handler import BPHandler, bp_handler
import time
from collections import defaultdict

import logging

log = logging.getLogger(__name__)


class STM32F4_Base(BPHandler):
    """
    This represents the "base" stuff in the STM32.
    All the things related to boot, reset, clocks, and the SysTick timer.
    """

    def __init__(self, model=TimerModel):
        self.model = model
        self.org_lr = None
        self.current_channel = 0
        self.addr2isr_lut = {
            '0x4000200': 0x32
        }
        self.irq_rates = {}
        self.name = 'STM32_TIM'

    @bp_handler(['HAL_Init'])
    def init(self, qemu, bp_addr):
        log.info("### STM32 HAL INIT ###")
        return False, None

    @bp_handler(['SystemInit'])
    def systeminit(self, qemu, bp_addr):
        log.info("### SystemInit ###")
        return False, None

    @bp_handler(['SystemClock_Config'])
    def systemclock_config(self, qemu, bp_addr):
        log.info("SystemClock_Config called")
        return True, 0

    @bp_handler(['HAL_RCC_OscConfig'])
    def rcc_osc_config(self, qemu, bp_addr):
        log.info("HAL_RCC_OscConfig called")
        return True, 0

    @bp_handler(['HAL_RCC_ClockConfig'])
    def rcc_clock_config(self, qemu, bp_addr):
        log.info("HAL_RCC_ClockConfig called")
        return True, 0

    @bp_handler(['HAL_SYSTICK_Config'])
    def systick_config(self, qemu, bp_addr):
        #rate = qemu.regs.r0
        rate = 5
        systick_irq = 15
        log.info("Setting SysTick rate to %#08x" % rate)
        self.model.start_timer('SysTick', systick_irq, rate)
        return True, 0

    @bp_handler(['HAL_SYSTICK_CLKSourceConfig'])
    def systick_clksourceconfig(selfself, qemu, bp_addr):
        src = qemu.regs.r0
        log.info("Setting SysTick source to %#08x" % src)
        return False, None

    @bp_handler(['HAL_InitTick'])
    def init_tick(self, qemu, bp_addr):
        systick_rate = 10
        systick_irq = 12
        log.info("Starting SysTick on IRQ %d, rate %d" %
                 (systick_irq, systick_rate))
        #self.model.start_timer("SysTick", systick_irq, systick_rate)
        #import ipdb; ipdb.set_trace()
        return True, 0

    @bp_handler(['Error_Handler'])
    def error_handler(self, qemu, bp_addr):
        self.model.stop_timer("SysTick")
        self.model.stop_timer("0x40000400")
        import ipdb
        ipdb.set_trace()
        return True, 0
