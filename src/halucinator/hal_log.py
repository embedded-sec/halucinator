'''
Uses config file format to control logging, first looks in local 
directory for config file and uses it if set, else uses the
default on from halucinator

For file format see: https://docs.python.org/3/library/logging.config.html#logging-config-fileformat
'''
import logging
import logging.config
from os import path


LOG_CONFIG_NAME = 'logging.cfg'
DEFAULT_LOG_CONFIG = path.join(path.dirname(__file__),'logging.cfg')
HAL_LOGGER = "HAL_LOG"

def getHalLogger():
    return logging.getLogger(HAL_LOGGER)

def setLogConfig():
    hal_log = getHalLogger()
    if path.isfile(LOG_CONFIG_NAME):
        hal_log.info("USING LOGGING CONFIG From: %s" % LOG_CONFIG_NAME)
        logging.config.fileConfig(fname=LOG_CONFIG_NAME, disable_existing_loggers=True)
    else:  # Default logging
        hal_log.info("USING DEFAULT LOGGING CONFIG")
        hal_log.info("This behavior can be overwritten by defining %s"% LOG_CONFIG_NAME)
        logging.config.fileConfig(fname=DEFAULT_LOG_CONFIG, disable_existing_loggers=False)
