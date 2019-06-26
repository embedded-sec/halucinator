# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. 
# Government retains certain rights in this software.

from ...peripheral_models.tcp_stack import TCPModel
from ..intercepts import tx_map, rx_map
from ..bp_handler import BPHandler, bp_handler
from collections import defaultdict, deque
import struct
import binascii
import os
import logging
from ...peripheral_models.timer_model import TimerModel

log = logging.getLogger("STM32F4Wifi")
log.setLevel(logging.DEBUG)

WIFI_OFF = 1
WIFI_IDLE = 2
WIFI_CONNECTED = 3

class STM32F4Wifi(BPHandler):

    def __init__(self, model=TCPModel):
        # Default values from recording
        self.wifi_state = WIFI_OFF
        # This thing uses a timer, in particular TIM1.
        # TODO: Make this generic by passing through to the Wifi_Module_Init function
        # We can do this easily after we can support calling a callback, and returning back into python.
        self.timer = TimerModel
        self.tim1 = 0x40000400
        self.model = model()

    @bp_handler(['wifi_init'])
    def wifi_init(self, qemu, bp_addr):
        '''
            Register the timers
        '''
        # TODO: Pass through to the timer init stuff
        #qemu.regs.pc = qemu.avatar.callables['WiFi_Module_Init']
        log.info("wifi_init called")
        #return False, None
        # Start the TIM1 timer
        wifi_timer_rate = 2
        self.timer.start_timer(self.tim1, 45, wifi_timer_rate)
        return True, 0
    @bp_handler(['wifi_wakeup'])
    def wifi_wakeup(self, qemu, bp_addr):
        '''
            Register the timers
        '''

        log.info("wifi_wakeup called.  Wakey-wakey!!")
        return True, 0

    @bp_handler(['Receive_Data'])
    def receive_data(self, qemu, bp_addr):
        log.info("Ignoring call to Receive_Data")
        return True, 0

    @bp_handler(['wifi_ap_start'])
    def wifi_ap_start(self, qemu, bp_addr):
        '''
            This version only supports the TCP/IP layer, do nothing
        '''

        log.info("wifi_ap_start called")
        return True, 0

    @bp_handler(['wifi_socket_server_open'])
    def wifi_socket_server_open(self, qemu, bp_addr):
        '''
            Should call listen()
            Arg1: Port number
            Arg2: The protocol (an enum, only TCP is supported)

        '''
        port = qemu.regs.r0
        log.info("wifi_socket_server_open called, listening on port %d" % port)
        self.model.listen(port)
        return True, 0

    @bp_handler(['wifi_socket_server_write'])
    def wifi_socket_server_write(self, qemu, bp_addr):
        '''
            This version only supports the TCP/IP layer, do nothing
        '''
        length = qemu.regs.r0
        data = qemu.read_memory(qemu.regs.r1, 1, length, raw=True)
        log.info("socket_server_write called, data: %s" % data)
        self.model.tx_packet(data)
        return True, 0

    @bp_handler(['Wifi_SysTick_Isr'])
    def wifi_systick_isr(self, qemu, bp_addr):
        '''
        The SysTick ISR used by the Wifi stack
        '''

        log.info("Wifi_SysTick_Isr called")
        # We do nothing here.  The STM32 Wifi stack does nasty stuff here to get the actual bytes in, and then hands them off to the other TIM handler.
        # We bypass the need for any of it.  Yay for HLE.
        return True, 0

    @bp_handler(['Wifi_TIM_Handler'])
    def wifi_tim_handler(self, qemu, bp_addr):
        """
        The STM32 Wifi stack's event dispatch queue
        Should be called over and over by a timer

        :param qemu:
        :param bp_addr:
        :return:
        """
        log.info("Wifi: Wifi_TIM_Handler called.")
        if self.wifi_state == WIFI_OFF and self.model.sock is None:
            # We just booted. Because we are not emulating 802.11, we just say that we're connected
            # The user app will call listen() for us, so just give it a nudge.
            # call `ind_wifi_connectedi`
            self.wifi_state = WIFI_IDLE
            log.info("Setting wifi_connected state")
            qemu.regs.pc = qemu.avatar.callables['ind_wifi_connected']
        # If a client has connected, and we don't know that yet, call the callback and set the mode.
        elif self.wifi_state == WIFI_IDLE and self.model.conn is not None:
            # We're connected!
            # Call `ind_wifi_socket_server_client_joined`
            self.wifi_state = WIFI_CONNECTED
            log.info("Setting wifi_socket_server_client_joined state")
            qemu.regs.pc = qemu.avatar.callables['ind_socket_server_client_joined']
        elif self.wifi_state == WIFI_CONNECTED:
            # Try to get some data!
            data = self.model.get_rx_packet()
            if data is not None:
                # We got one!
                log.info("Wifi: Received %s" % repr(data))
                RX_DATA_BUF = 0x200f0000
                # FIXME: It would be nice if we had a better way to do this.  We don't, but that's fine.    
                data += '\0'
                qemu.write_memory(RX_DATA_BUF, 1, data, len(data), raw=True) # Null-terminate
                # Call `ind_wifi_socket_data_received`
                qemu.regs.r0 = 0 #Socket id
                qemu.regs.r1 = RX_DATA_BUF # buffer
                qemu.regs.r2 = len(data)  # length
                qemu.regs.r3 = len(data)  # Chunk size.  TODO: What is this, even?
                qemu.regs.pc = qemu.avatar.callables['ind_wifi_socket_data_received']
            elif self.model.conn is None:
                # The client left!
                # Call `ind_wifi_socket_server_client_left`
                log.info("Client left, setting wifi_socket_server_client_left state")
                self.wifi_state = WIFI_IDLE
                qemu.regs.pc = qemu.avatar.callables['ind_socket_server_client_left']
        else:
            # No callback needed
            return True, 0
        # We are calling something.  Do it.
        return False, None # So the callback gets taken
