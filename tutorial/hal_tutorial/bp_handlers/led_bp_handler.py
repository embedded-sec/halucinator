# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.

from os import sys, path
# NOTE:
# We import LED Model here
from ..peripheral_models.led_peripheral import LEDModel
from halucinator.bp_handlers import BPHandler, bp_handler
import logging
log = logging.getLogger(__name__)

from halucinator import hal_log
hal_log = hal_log.getHalLogger()


class LEDHandler(BPHandler):

    def __init__(self, map_dict=None):
        self.model = LEDModel
        if map_dict == None:
            self.led_map = {}
        else:
            self.led_map = map_dict

    def get_id(self, led_id):
        try:
            led_id = self.led_map[led_id]
        except (KeyError):
            led_id = led_id
        return led_id

    @bp_handler(['My_BSP_LED_Init'])
    def led_init(self, target, bp_addr):
        log.debug("Init Called")
        # STEP 1.
        # Use target's get_arg method to get the LED arg 0 the function.
        # Then use self.get_id to convert it an id and
        # call self.model.off(led_id) to set the LED to off
        
        return True, None  # Intercept and Return type is void

    @bp_handler(['My_BSP_LED_On'])
    def on(self, target, bp_addr):
        log.debug("LED On Called")
        # STEP 2.
        # Use target's get_arg method to get the LED arg 0 the function.
        # Then use self.get_id to convert it an id and
        # call self.model.on(led_id) to set the LED to on in the peripheral model
        
        return True, None  # Return type is void

    @bp_handler(['My_BSP_LED_Off'])
    def off(self, target, bp_addr):
        log.debug("LED Off Called")
        # STEP 3.
        # Use target's get_arg method to get the LED arg 0 the function.
        # Then use self.get_id to convert it an id and
        # call self.model.on(led_id) to set the LED to on in the peripheral model
        
        return True, None  # Return type is void

 