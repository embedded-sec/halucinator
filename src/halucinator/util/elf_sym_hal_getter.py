# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.

import yaml
from . import hexyaml
import angr
import os


def load_binary(filename):
    '''
        Loads binary using angr's cle loader
    '''
    print(("Loading", filename))
    loader = angr.cle.loader.Loader(filename, auto_load_libs=False,
                                    use_system_libs=False)
    return loader


def build_addr_to_sym_lookup(binary):
    '''
        Builds a look up table that maps an address to a function
        Lut has every address of a function in it and value is a symbol
        Returns:
            sym_lut(dict): {addr: Symbol}
    '''
    sym_lut = {}
    loader = load_binary(binary)
    for addr, sym in list(loader.main_object.symbols_by_addr.items()):
        if sym.is_function:
            start_addr = addr & 0xFFFFFFFE  # Clear Thumb bit
            for a in range(start_addr, start_addr+sym.size, 2):
                sym_lut[a] = sym
    return sym_lut


def get_functions_and_addresses(binary):

    loader = load_binary(binary)

    functions = {}
    for symbol in loader.symbols:
        if symbol.is_function:
            # Clear Thumb bit
            functions[symbol.name] = symbol.rebased_addr & 0xFFFFFFFE
    return functions


def format_output(functions, base_addr=0x00000000, entry=0):
    '''
        Converts the symbol dictionary to the output format used by halucinator

        TODO: Change to be use symbol as the key, as the same address can
        have the multiple symbols
        Also would require changin LibMatch
    '''
    out_dict = {'architecture': 'ARMEL',
                'base_address': base_addr,
                'entry_point':  entry,

                }
    symbols = {}
    for fname, addr in list(functions.items()):
        symbols[addr] = fname
    out_dict['symbols'] = symbols

    return out_dict


if __name__ == '__main__':
    '''
    Gets Symbols from elf file using the symbols table in the elf
    '''
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('-b', '--bin', required=True,
                   help='Elf file to get symbols from')
    p.add_argument('-o', '--out', required=False,
                   help='YAML file to save output to' +
                   'if will be output to (--bin).yaml')

    args = p.parse_args()
    if args.out == None:
        args.out = os.path.splitext(args.bin)[0] + "_addrs.yaml"

    functions = get_functions_and_addresses(args.bin)
    with open(args.out, 'w') as outfile:
        out_dict = format_output(functions)
        yaml.safe_dump(out_dict, outfile)
