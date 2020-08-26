# Developers Guide

## Building own bp_handlers and peripheral models

Depending on you the type handlers and models you are building there are two
ways to build them.  If they are generic and will benefit the wider community
add them directly to the bp_handler's or peripheral_models directory. 
(Pull requests are wanted)

If for what ever reason you want to keep them seperate from mainline halucinator
you can build them in your own module, and install that module in the same virtual
environment as halucinator.

For example let say you modules for an OS - `my_os`. 
You could create a python module with following directory structure

```txt
my_os 
+-> hal_my_os
    +-> filesystem.py
    +-> ...
+-> setup.py
+-> README.md
```
The  would look create and install the module `hal_my_os`. It contents look 
something like below, and installed from the top level directory (`my_os`) with
`pip install -e .`.

```py
from setuptools import setup, find_packages

packages = find_packages()

setup(
    name='hal_my_os',
    version='0.1',
    python_requires='>=3.5',
    description='Halucinator module for My OS',
    packages=packages,
    install_requires=[
        # Any specific packages you require
    ],
)

```
`filesystem.py` would contain break point handler classes that subclass `BPHandler`
It with it would contain multiple decorated methods that are called when 
these functions execute in the firmware.  Each `@bp_handler` declaration
contains a list of firmware functions this method handles.  The handler needs
to return two values a bool, and a value.  The bool determine if the firmware
function is intercepted (ie not executed if True. If false function is executed
after the python method), and return value.  The return value put into the emulated 
systems as if the firmware function executed and returned this value. `None`
means no return value, and return values should be `None` if function is not
intercepted.  Below is a stub for `filesystem.py`.

```py
from halucinator.bp_handlers.bp_handler import BPHandler, bp_handler
import logging
import os

log = logging.getLogger(__name__)

class Filesystem(BPHandler):
    def __init__(self, model=(desired file system model)):
        self.model = model

    @bp_handler(['write'])
    def my_os_write(self, target, bp_addr):
        fd = target.get_arg(0)
        buf_ptr = target.get_arg(1)
        buf_len = target.get_arg(2)
        buf = target.read_memory(buf_ptr, 1, buf_len, raw=True)
        len_written = model.write(fd, buf)
        return True, len(len_written)

```

The configuration file entry to use the Filesystem Break point handlers would
look like this

```yaml
  - class: hal_my_os.Filesystem
    function: write
```

## Logging

Halucinator uses the python module `logging` for logging. Each
file gets its logger using `logging.getLogger(__name__)`.
Halucinator also has a special log `HAL_LOG` that can be used for
messages that will are useful beyond just a specific module. If you
want to use it import halucinator.hal_log, and call `getHalLogger()`.

Logging is configured using a file, as defined by [https://docs.python.org/3/library/logging.config.html#logging-config-fileformat].  By default 
`halucinator/src/halucinator/logging.cfg` is used, which defines some sane defaults
for using halucinator. You can override the default by
defining a `logging.cfg` in the directory you run halucinator from.
Loggers are hierachial, so for example if set parameters on the `halucinator`
logger it will apply them to all sub modules of halucinator. 

An example of how you can override the logging configuration is below. 
If saved to `logging.cfg` in you local directory. It will set `halucinator` to
the INFO level and your module -- `hal_my_os` -- to DEBUG.

```ini
[loggers]
keys=root,halucinator.main,HAL_LOG,hal_my_os

[handlers]
keys=consoleHandler

[formatters]
keys=sampleFormatter

[logger_root]
level=ERROR
handlers=consoleHandler

[logger_halucinator.main]
level=INFO
handlers=consoleHandler
propagate=0
qualname=halucinator.main

[logger_HAL_LOG]
level=INFO
handlers=consoleHandler
propagate=0
qualname=HAL_LOG

[logger_halucinator]
level=INFO
handlers=consoleHandler
propagate=0
qualname=halucinator

[logger_hal_my_os]
level=DEBUG
handlers=consoleHandler
propagate=0
qualname=hal_my_os

[handler_consoleHandler]
class=StreamHandler
level=DEBUG
formatter=sampleFormatter
args=(sys.stdout,)

[formatter_sampleFormatter]
format=%(name)s|%(levelname)s|  %(message)s
```
