# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a
# non-exclusive license for use of this work by or on behalf of the U.S.
# Government. Export of this data may require a license from the United States
# Government.

'''
    Creates a config file using memory description, intercepts and a elf
    file
'''
from tools import hexyaml
import yaml
import os

from tools.elf_sym_hal_getter import get_functions_and_addresses


def get_addr_for_intercepts(intercepts, firmware):
    # TODO Replace below call with binary analysis
    funct_2_addr = get_functions_and_addresses(firmware)
    mapped_intercepts = []
    for inter in intercepts:
        funct = inter['function']
        if funct in funct_2_addr:
            inter['addr'] = funct_2_addr[funct]
            mapped_intercepts.append(inter)
        else:
            print("WARNING: No address found for: ", funct)

    return mapped_intercepts


def replace_memory_keywords(config, keyword, value):
    '''
        Replaces keywords in memory template with value
    '''
    mems = config['memories']
    for mem_name, mem_config in list(mems.items()):
        for key in mem_config:
            if mem_config[key] == keyword:
                print("Replacing {%s: %s} with {%s:%s}" %
                      (key, mem_config[key], key, value))
                mem_config[key] = value


def get_emulator_config(memories, intercepts, firmware):
    config = memories

    replace_memory_keywords(config, '<FIRMWARE>',
                            os.path.split(firmware)[-1] + '.bin')
    mapped_intercepts = get_addr_for_intercepts(intercepts, firmware)
    config['intercepts'] = mapped_intercepts
    return config


if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('-f', '--firmware', required=True,
                   help='firmware')
    p.add_argument('-m', '--memories', required=True,
                   help='Memory description for device')
    p.add_argument('-i', '--intercepts', required=True,
                   help='Mapping of intercepts functions to intercept classes')
    p.add_argument('-c', '--config',
                   help='Output config file (.yaml) if not provided firmware' +
                   'name append with _config.yaml')
    p.add_argument('--ivt', type=int, default=0,
                   help='Interrupt vector table offset (used to get entry, and sp')

    args = p.parse_args()

    with open(args.memories, 'rb') as mem_file:
        memories = yaml.load(mem_file)

    with open(args.intercepts, 'rb') as int_file:
        intercepts = yaml.load(int_file)

    config = get_emulator_config(memories, intercepts, args.firmware)

    if args.config == None:
        config_file = os.path.splitext(args.firmware)[0] + "_config.yaml"
    else:
        config_file = args.config
    with open(config_file, 'wb') as outfile:
        yaml.safe_dump(config, outfile)
