# UART Deep Dive

In this tutorial we will go over how HALucinator sends and receives
data over the UART. First we will discuss the bp handlers used to intercept
execution of the UART HAL.  We'll then discuss the peripheral model used
by these bp handlers, and the external devices used to communicate with
the peripheral model

##  BPHandler Deep Dive

Recall that the firmware uses four functions to interact with the UART.
These are:

* HAL_UART_Init
* HAL_UART_Transmit_IT
* HAL_UART_Receive_IT
* HAL_UART_GetState

Our intercept config file `~/halucinator/src/test/STM32/example/Uart_Hyperterminal_IT_O0_config.yaml`
specifies intercepts for each of these functions. Shown below.

```yaml
- class: halucinator.bp_handlers.stm32f4.stm32f4_uart.STM32F4UART
  function: HAL_UART_Init
  symbol: HAL_UART_Init
- class: halucinator.bp_handlers.stm32f4.stm32f4_uart.STM32F4UART
  function: HAL_UART_GetState
  symbol: HAL_UART_GetState
- class: halucinator.bp_handlers.stm32f4.stm32f4_uart.STM32F4UART
  function: HAL_UART_Transmit_IT
  symbol: HAL_UART_Transmit_IT
- class: halucinator.bp_handlers.stm32f4.stm32f4_uart.STM32F4UART
  function: HAL_UART_Receive_IT
  symbol: HAL_UART_Receive_IT
```

Each UART intercept uses the
`halucinator.bp_handlers.stm32f4.stm32f4_uart.STM32F4UART` class, which are
implemented in `~/halucinator/src/halucinator/bp_handlers/stm32f4/stm32f4_uart.py`
Let's open it up and examine it.

Starting from the top. This imports the peripheral model `UartPublisher`, the
`BPHandler` class, `bp_handler` decorator, and sets up logging.

```py
from ...peripheral_models.uart import UARTPublisher
from ..bp_handler import BPHandler, bp_handler
import logging
log = logging.getLogger(__name__)

from ... import hal_log
hal_log = hal_log.getHalLogger()
```

Though out halucinator logging should be setup this way and used instead of print 
for debugging this makes it easy to turn on and off on a per file basis
using a configuration file.  Generally two logs are used: `log`, which captures stuff  
relevant to just this file, and `hal_log` which logs things that are of 
interest across halucinator. If in question just use `log`.

It then creates a class that subclasses (`BPHandler`) and assigns `self.model`
to the `UARTPublisher` peripheral model.

```python
class STM32F4UART(BPHandler):
    def __init__(self, impl=UARTPublisher):
        self.model = impl
```

Then it implements the handler for `HAL_UART_Init`

```python
    @bp_handler(['HAL_UART_Init'])
    def hal_ok(self, qemu, bp_addr):
        log.info("Init Called")
        return True, 0
```

The decorator `@bp_handler` identifies this method as a bp handler method.
The decorator takes either no arguments, in which case only one bp_handler per class
can be implemented or a list of function names.  The function names are valid
values for the `function` key in the intercept config. Note: for 
historical reasons multiple can be specified but one name should be sufficient.

All `@bp_handlers` methods take as parameters `(self, qemu, bp_addr)`:

* `self`:  The instance of this class
* `qemu`:  Is a subclass of (Avatar2's qemu target)[https://avatartwo.github.io/avatar2-docs/avatar2.targets.html#module-avatar2.targets.target].  Our subclasses are in `src/halucinator/qemu_targets`
and abstract binary convention details away. This allows reading and 
writing the emulators registers, memory, and control over the emulator
* `bp_addr`: The address of the break point

The handler returns two values a boolean (`Intercept`) and a number(`Ret_Val`).
If `Intercept` is `True` the function is intercepted and the function will not 
be executed in the emulator. `Ret_Val` will be returned for the function's 
return value. This makes it appear the function executed and returns `Ret_Val`.
set `Ret_Val` to `None` if function being intercepted does not return a value.
If `Intercept` is `False` execution  continues, the function is executed, and 
`Ret_Val` is ignored. Best practice in this case is to set `Ret_Val` to `None`. 
Not intercepting execution is useful if you want to monitor 
the execution of a function but still allow it to execute.

Looking back at the `HAL_UART_Init` bp handler, you should now see that it logs
the call to the function, prevents the function from executing and returns 0. 
Zero is `HAL_OK`, thus execution continues with the firmware behaving as if the 
UART was initialized correctly.

Similarly the `HAL_UART_GetState` bp handler just returns `0x20`, the value
indicating it is ready.

Now lets look at how data is transmitted.  The `handle_tx` method is designed
to intercept any of the `HAL_UART_Transmit*` variants from STM's HAL.  These functions
have the following prototype.

```c
HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef *huart, uint8_t *pData, uint16_t Size);
```

* `huart`  is a pointer to a struct that captures UART specific details.  Most 
important is the first entry in the struct is a pointer to the hardware address
that identifies which UART is used.
* `pData`  pointer to the buffer of data to transmit
* `Size`   size of data in buffer to transmit.

Below is the handler used to replace execution of this function in halucinator.

```python
    @bp_handler(['HAL_UART_Transmit', 'HAL_UART_Transmit_IT', 'HAL_UART_Transmit_DMA'])
    def handle_tx(self, qemu, bp_addr):
        '''
            Reads the frame out of the emulated device, returns it and an 
            id for the interface(id used if there are multiple ethernet devices)
        '''
        huart = qemu.get_arg(0)
        hw_addr = qemu.read_memory(huart, 4, 1)
        buf_addr = qemu.get_arg(1)
        buf_len = qemu.ret_arg(2)
        data = qemu.read_memory(buf_addr, 1, buf_len, raw=True)
        hal_log.info("UART TX:%s" % data)
        self.model.write(hw_addr, data)
        return True, 0
```

You can see it gets the `huart` pointer from arg 0 and dereferences it by reading
memory at that location to get the hardware address.  It then gets the `buf_addr`
from arg 1, and `buf_len` from arg 2, and reads the buffer from memory. It logs 
the data, and writes it to the model, using the hardware as the id for message.

Receiving data works in a similar manner.  The firmware calls 
`HAL_UART_Receive_IT` which has the same c prototype as it's transmit counter part.
Which gets intercepted and handled by the `handle_rx` method below.  The handler
gets the hardware address and size, then calls the model to get data, blocking until
it has arrived.  It then writes the data to the buffer in the firmware's memory.
The handler then return's `True, 0` causing the `HAL_UART_Receive_IT` execution
to be skipped, and appear like it executed and returned 0 (`HAL_OK`).  

```python
    @bp_handler(['HAL_UART_Receive', 'HAL_UART_Receive_IT', 'HAL_UART_Receive_DMA'])
    def handle_rx(self, qemu, bp_handler):
        huart = qemu.get_arg(0)
        hw_addr = qemu.read_memory(huart, 4, 1)
        size = qemu.get_arg(2)
        log.info("Waiting for data: %i" % size)
        data = self.model.read(hw_addr, size, block=True)
        hal_log.info("UART RX: %s" % data)

        qemu.write_memory(qemu.get_arg(1), 1, data, size, raw=True)
        return True, 0
```

## UART Peripheral Model Deep Dive

Now lets look at the Peripheral Model.
Recall the purpose of the model is to implement the core components of what a
peripheral does.  In the case of the UART, this is sending and receiving characters.
There are lots of different HAL's used to send/receive data on a UART, the order of
parameters and types of the parameters will vary. These low level details
are implemented in the BP handlers, but the core functionality of sending/receiving
bytes is implemented in the peripheral model. By abstracting the device we
reduce the amount of work to implement each HAL.


The UART Peripheral model is found in 
`~/halucinator/src/halucinator/peripheral_models/uart.py`

Prior to this creation of the class you will notice that is sets up logging 
like the UART BP handler.

Now looking at the creation of the class.

```python
# Register the pub/sub calls and methods that need mapped
@peripheral_server.peripheral_model
class UARTPublisher(object):
    rx_buffers = defaultdict(deque)
```

The class is decorated with `@peripheral_server.peripheral_model` This tells
the peripheral server that this class is going to send/receive data from the
peripheral server.  You will also notice that all the methods are `@classmethod`
this is because these classes are never instantiated.  As a result, any state
such as the receive buffers (`rx_buffers`) need to be saved at the class level.

There are four methods in this class `write`, `read`, `read_line`, `rx_data`. We will look
at `write` and `rx_data` first then discuss the read methods. 
The write method is below.

```python
    @classmethod
    @peripheral_server.tx_msg
    def write(cls, uart_id, chars):
        '''
           Publishes the data to sub/pub server
        '''
        log.info("Writing: %s" % chars)
        msg = {'id': uart_id, 'chars': chars}
        return msg
```

Notice the `write` method is decorated with the `@classmethod` and `@peripheral_server.tx_msg`
The `@peripheral_server.tx_msg` decorator makes it so this method's return
value is serialized and published by the peripheral server with topic
`Peripheral.<ClassName>.<method_name>`.  
`write` takes an identifier, and the data (`chars`) as parameters and puts these
in a dictionary and returns the dictionary (`msg`).  Thus, the dictionary is published by the peripheral
server under the topic `Peripheral.UARTPublisher.write`.  As you will see later, 
our external devices `hal_dev_uart` subscribes to this topic and prints out 
what it receives.

Now lets look at the `rx_data` method.

```python
    @classmethod
    @peripheral_server.reg_rx_handler
    def rx_data(cls, msg):
        '''
            Handles reception of these messages from the PeripheralServer
        '''
        log.debug("rx_data got message: %s" % str(msg))
        uart_id = msg['id']
        data = msg['chars']
        cls.rx_buffers[uart_id].extend(data)
```

This method is decorated with the `@peripheral_server.reg_rx_handler` decorator.
When used on a method this registers this method as the handler for topics 
sent to the peripheral server with topic `Peripheral.<ClassName>.<method_name>.`
So this method will receive all traffic sent to topic `Peripheral.UARTPublisher.rx_data`.
In this case the msg received is a dictionary with keys `id`, and `chars`,
matching those send by `write`.  It saves `chars` to a dictionary of deques (a stack)
with the deque used being selected by the id.  By saving it to the deque
we make receiving data asynchronous from the firmware's execution of it's UART 
receive function that gets the data.

Recall that the model's `read` function was called by the bp handler for 
`HAL_UART_Receive_IT`. Let look at what it does.  

```python
    @classmethod
    def read(cls, uart_id, count=1, block=False):
        '''
            Gets data previously received from the sub/pub server
            Args:
                uart_id:   A unique id for the uart
                count:  Max number of chars to read
                block(bool): Block if data is not available
        '''
        log.debug("In: UARTPublisher.read id:%s count:%i, block:%s" %
                  (hex(uart_id), count, str(block)))
        while block and (len(cls.rx_buffers[uart_id]) < count):
            pass
        log.debug("Done Blocking: UARTPublisher.read")
        buffer = cls.rx_buffers[uart_id]
        chars_available = len(buffer)
        if chars_available >= count:
            chars = [buffer.popleft() for _ in range(count)]
            chars = ''.join(chars).encode('utf-8')
        else:
            chars = [buffer.popleft() for _ in range(chars_available)]
            chars = ''.join(chars).encode('utf-8')

        log.info("Reading %s"% chars)
        return chars
```

It takes in:

* `uart_id`: The id for the UART
* `count`: Number of bytes to read.
* `block` a boolean that sets if this method should block if data is not available

If `block` is `True` this method will wait in a 
loop until `count` bytes are available in `rx_buffers` for the given 
`uart_id`.  When data is available it reads out all 
available data up to `count` bytes and returns them.  If `block` is `False`
it will return as many characters that are currently available -- including 
zero -- up to `count`.  

The `read_line` method works similar to `read` except it reads until `\n` is
found before returning data.

You should now understand how halucinator executes firmware, intercepts functions,
executes bp handlers to replace those functions, and sends and receives data
using the peripheral server.

We will now look at how an external devices communicates with the peripheral 
server.

## External Devices

For this we will look at the `hal_dev_uart` command works.  This is actually 
an entry point setup when we installed halucinator that calls 
`src/halucinator/external_devices/uart.py`'s `main` function.  Lets look at it.  
`main` is located at the end of the file.

```python
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
```

It uses argparse to get a number of parameters which the defaults should work
unless you are running multiple instance of halucinator.
The `-r`, `-t` select ports used to receive and transmit data with the halucinator
peripheral server.  The `-i` specifies the uart id to interact with.  It must match
the `id` key in the msg sent by the uart peripheral handler for data to be received
inside halucinator. `-n` will append a new line character to data entered in. 

Moving down `main`

```python
    io_server = IOServer(args.rx_port, args.tx_port)
    uart = UARTPrintServer(io_server)

    io_server.start()
```

Next we instantiate an `IOServer`.  This is a helper class that handles the
zero mq communication with halucinator and creates threads need to communicate 
asynchronous with it. We won't cover it in this tutorial, but refer you to 
its source `src/halucinator/external_devices/io.server.py` for more info. 
`main` then instantiates a `UartPrintServer` class passing the `IOServer`as an
argument, and starts the `IOServer`.

We then enter a `while(1)` loop that reads input from the terminal and
uses `uart` to send it.  A KeyboardInterrupt 
(e.g., pressing `Ctrl c`) or an empty input will exit the loop. After
which the `IOServer` is stopped and the program exits.

```python
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
```

Let's now look at the `UARTPrintServer` class

```python
class UARTPrintServer(object):

    def __init__(self, ioserver):
        self.ioserver = ioserver
        ioserver.register_topic(
            'Peripheral.UARTPublisher.write', self.write_handler)

    def write_handler(self, ioserver, msg):
        txt = msg['chars'].decode('latin-1')
        print("%s" % txt, end=' ', flush=True)

    def send_data(self, id, chars):
        d = {'id': id, 'chars': chars}
        log.debug("Sending Message %s" % (str(d)))
        self.ioserver.send_msg('Peripheral.UARTPublisher.rx_data', d)

```

It has three methods `__init__` which subscribes to the `Peripheral.UartPublish.write`
topic with the `IOServer` and registers its `write_handler` to handle the received
message.  The `write_handler` simply prints the data out.  Finally the `send_data`
takes an id and chars to send, composes the dictionary expected by the uart model
and uses the `IOServer` to send the message using `Peripheral.UARTPublisher.rx_data`
as the topic.

## Conclusion

You should now understand the code that halucinator executes when it calls
the HAL functions to send and receive data, and how that data gets into and 
out of halucinator.  In the next tutorial, we will implement new bp handlers,
peripheral model, and external device. [4_extending_deep_dive.md](4_extending_deep_dive.md)