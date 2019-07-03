# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a
# non-exclusive license for use of this work by or on behalf of the U.S.
# Government. Export of this data may require a license from the United States
# Government.

from . import peripheral_server
from collections import deque, defaultdict
from .interrupts import Interrupts
from threading import Thread, Event
import logging
import time
log = logging.getLogger("TimerModel")
log.setLevel(logging.DEBUG)


# Register the pub/sub calls and methods that need mapped
@peripheral_server.peripheral_model
class TimerModel(object):

    active_timers = {}
    @classmethod
    def start_timer(cls, name, isr_num, rate):
        log.info("Starting timer: %s" % name)
        if name not in cls.active_timers:
            stop_event = Event()
            t = TimerIRQ(stop_event, name, isr_num, rate)
            cls.active_timers[name] = (stop_event, t)
            t.start()

    @classmethod
    def stop_timer(cls, name):
        if name in cls.active_timers:
            (stop_event, t) = cls.active_timers[name]
            stop_event.set()

    @classmethod
    def clear_timer(cls, irq_name):
        # cls.stop_timer(name)
        Interrupts.clear_active(irq_name)

    @classmethod
    def shutdown(cls):
        for key, (stop_event, t) in list(cls.active_timers.items()):
            stop_event.set()


class TimerIRQ(Thread):
    def __init__(self, event, irq_name, irq_num, rate):
        Thread.__init__(self)
        self.stopped = event
        self.name = irq_name
        self.irq_num = irq_num
        self.rate = rate

    def run(self):
        while not self.stopped.wait(self.rate):
            log.info("Sending IRQ: %s" % self.irq_num)
            Interrupts.set_active(self.name)
            Interrupts.trigger_interrupt(self.irq_num)
            # call a function
