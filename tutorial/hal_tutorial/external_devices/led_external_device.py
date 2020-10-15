# Copyright 2020 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.


from halucinator.external_devices.ioserver import IOServer
from halucinator.external_devices.uart import UARTPrintServer
import logging
log = logging.getLogger(__name__)

#  This is our extenal device calass that is going
# to handle LEDs
class LEDDevice(object):
   
    def __init__(self, ioserver):
        self.ioserver = ioserver
        # STEP 1 
        # Notice saving the ioserver (above) and registing for the topic
        # There is a typo in topic class name that makes it so this
        # won't receive messages from your peripheral model.
        # It needs to match your peripheral_model class name 
        topic = 'Peripheral.XXX_Model.led_status'

        log.debug("Registering for topic %s" % topic)
        ioserver.register_topic(topic, self.write_handler)

    def write_handler(self, ioserver, msg):
        log.debug("Got status %s" % str(msg))
        # STEP 2
        # You will msg will be a dict like {'id': LED_ID, 'status':<boolean>}
        # Use print so message always shows up with format like
        # "LED: %s is %s" % (led_id, state) where state is 'On' or 'Off'
        


def main():
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('-r', '--rx_port', default=5556,
                   help='Port number to receive zmq messages for IO on')
    p.add_argument('-t', '--tx_port', default=5555,
                   help='Port number to send IO messages via zmq')
    p.add_argument('-i', '--id', default=0x20000ab0, type=int,
                   help="Id to use when sending data")
    p.add_argument('-n', '--newline', default=False, action='store_true',
                   help="Append Newline")
    args = p.parse_args()

    import halucinator.hal_log as hal_log
    hal_log.setLogConfig()

    io_server = IOServer(args.rx_port, args.tx_port)
    uart = UARTPrintServer(io_server)

    # STEP 3
    # Instantiate your LEDDevice class and as led and pass io_server to its initializer
    led = LEDDevice(io_server)
    io_server.start()

    try:
        while(1):
            data = input()
            log.debug("Got %s" % str(data))
            if args.newline:
                data +="\n"
            if data == '\\n':
                data = '\r\n'
            elif data == '':
                break
            #d = {'id':args.id, 'data': data}
            uart.send_data(args.id, data)
    except KeyboardInterrupt:
        pass
    log.info("Shutting Down")
    io_server.shutdown()


if __name__ == '__main__':
    main()