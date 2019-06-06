# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC 
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a 
# non-exclusive license for use of this work by or on behalf of the U.S. 
# Government. Export of this data may require a license from the United States 
# Government.


from ...peripheral_models.gpio import GPIO
from ..intercepts import tx_map, rx_map
from ..bp_handler import BPHandler, bp_handler
from collections import defaultdict, deque
import struct
import binascii
import os


class STM32F4GPIO(BPHandler):
    
    def __init__(self, model=GPIO):
        self.model = GPIO
        # Default values from recording
        self.phy_registers = {1:0x786d, 0x10:0x115, 0x11:0, 0x12:0x2c00}

    def get_id(self, port, pin):
        '''
            Creates a unique id for the port and pin
        '''
        return hex(port)+'_'+str(pin)


    @bp_handler(['HAL_GPIO_EXTI_IRQHandler'])  
    def handle_exti(self, qemu, bp_addr):
        print "HAL_GPIO_EXTI_IRQHandler calling HAL_GPIO_EXTI_Callback"
        print "GPIO=", hex(qemu.regs.r0)
        callback_addr = qemu.avatar.callables['HAL_GPIO_EXTI_Callback']
        # Effectively does tail call so HAL_GPIO_EXTI_Callback will return
        # without executing HAL_GPIO_EXTI_IRQHandler
        qemu.regs.pc = callback_addr  
        return False, None

    @bp_handler(['HAL_GPIO_Init'])
    def gpio_init(self, qemu, bp_addr):
        return True, 0

    @bp_handler(['HAL_GPIO_DeInit'])
    def gpio_deinit(self, qemu, bp_addr):
        return True, 0

    @bp_handler(['HAL_GPIO_WritePin'])
    def write_pin(self, qemu, bp_addr):
        '''
            Reads the frame out of the emulated device, returns it and an 
            id for the interface(id used if there are multiple ethernet devices)
            
        '''
        # void HAL_GPIO_WritePin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin, 
        #                        GPIO_PinState PinState);
        port = qemu.regs.r0
        pin = qemu.regs.r1
        value = qemu.regs.r2
        gpio_id = self.get_id(port, pin)
        self.model.write_pin(gpio_id, value)
        intercept = True # Don't execute real function
        ret_val = None # Return HAL_OK
        return intercept, ret_val


    @bp_handler(['HAL_GPIO_TogglePin'])  
    def toggle_pin(self, qemu, bp_addr):
        '''
            Toggles the pin
            
        '''
        #print "In Toggle GPIO"
        # void HAL_GPIO_TogglePin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin);
        port = qemu.regs.r0
        pin = qemu.regs.r1
        gpio_id = self.get_id(port, pin)
        self.model.toggle_pin(gpio_id)
        intercept = True # Don't execute real function
        ret_val = None # Return void
        return intercept, ret_val


    @bp_handler(['HAL_GPIO_ReadPin'])
    def read_pin(self, qemu, bp_addr):
         # GPIO_PinState HAL_GPIO_ReadPin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin);
        port = qemu.regs.r0
        pin = qemu.regs.r1
        gpio_id = self.get_id(port, pin)
        ret_val = self.model.read_pin(gpio_id)       
        return True, ret_val

        

    # HAL_StatusTypeDef HAL_GPIO_LockPin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin);
    # void HAL_GPIO_EXTI_IRQHandler(uint16_t GPIO_Pin);
    # void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin);
