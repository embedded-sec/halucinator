# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.


'''
    This file is primarily illustrate how to generate the config file 
    that should be run with emulate_binary.py

    It generates a config for Nucleo15_Blinky
'''
import hexyaml
import yaml


def get_memories():
    '''
    Memories have the following form
    'name': {
        'base_addr': <int> required
        'size': <int> required
        'permissions': <str> optional if provided must one of [r--, rw-, rwx],
        'emulate': <str> optional must be class in src/peripheral_emulators
        'file': <str> optional abs path, or relative to this config file
    }
    '''
    memories = {}
    memories['flash'] = {'file': 'STM32CubeL1_Blinky.bin',
                         'permissions': 'r-x',
                         'base_addr': 0x08000000,
                         'size': 0x1000000,
                         'name': 'flash'}

    memories['alias'] = {'file': 'STM32CubeL1_Blinky.bin',
                         'permissions': 'r-x',
                         'base_addr': 0x00000000,
                         'size': 0x1000000,
                         'name': 'alias'}

    memories['ram'] = {'base_addr': 0x20000000,
                       'size': 0x14000,
                       'name': 'ram'}

    return memories


def get_peripherals():
    peripherals = {
        'logger': {
            'permissions': 'rw-',
            'emulate': 'GenericPeripheral',
            'base_addr': 0x40000000,
            'size': 0x20000000,
            'name': 'peripherals'
        }
    }

    return peripherals


def get_intercepts():
    '''
    Intercepts have the following form
    {   
        'class': <class from intercepts.py> required
        'addr':  <int> required (address to intercept),
        'function': <str> required,
        'class_args': {}  <not used yet>
     }
    '''
    SysInit = {'class': 'VoidIntercept',
               'addr': 0x80001a8,
               'function': 'SystemInit',
               'class_args': None
               }

    SystemClock_Config = {'class': 'VoidIntercept',
                          'addr': 0x80002dc,
                          'function': 'SystemClock_Config',
                          'class_args': None
                          }

    DelayIntercept = {'class': 'DelayIntercept',
                      'addr': 0x800020c,
                      'function': 'LL_mDelay',
                      'class_args': None
                      }

    return [SysInit, SystemClock_Config, DelayIntercept]


def main(config_file):

    config = {'init_memory': 'flash',
              'memories': get_memories(),
              'peripherals': get_peripherals(),
              'intercepts': get_intercepts()}

    with open(config_file, 'wb') as outfile:
        yaml.dump(config, outfile, indent=4)


if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument("-c", '--config', type=str,
                   help="Output name for config file (.yaml)")
    args = p.parse_args()
    main(args.config)
