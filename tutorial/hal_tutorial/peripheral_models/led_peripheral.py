# Copyright 2020 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.

from halucinator.peripheral_models import peripheral_server
import logging
from itertools import repeat

log = logging.getLogger(__name__)

#STEP 1.  Register the class with the peripheral server 
#    using the @peripheral_server.peripheral_model decorator

class LEDModel(object):
    

    @classmethod
    #STEP 2.  Add the @peripheral_server.tx_msg decorater to transmit the return 
    #    value of this method out the peripheral server with topic 
    #    'Peripheral.LEDModel.led_status' 
    
    def led_status(cls, led_id, status):
        log.debug("LED Status %s: %s" %(led_id, status))
        #STEP 3. Compose a dictionary with the keys 'id' and 'status' and return it 
        

    @classmethod
    def led_off(cls, led_id):
        log.debug("LED Off %s" % (led_id))
        #STEP 4.  Call the led_status method providing False for off
        
        

    @classmethod
    def led_on(cls, led_id):
        log.debug("LED On %s" % (led_id))
        #STEP 5.  Call the led_status method providing True for On
        