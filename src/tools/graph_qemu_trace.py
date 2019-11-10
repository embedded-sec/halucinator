Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains certain rights in this software.

import networkx as nx
import os


BLOCK_DELIMITER = '\n'
BLOCK_KEY = 1


class Block(object):
    count = 0

    def __init__(self, block_str, sym_lut=None):
        self.block_str = block_str
        self.name = self.parse_name(block_str)
        self.addr = int(self.name, 16)
        self.function = 'None'
        if sym_lut != None:
            if self.addr in sym_lut:
                self.function = sym_lut[self.addr].name
        self.__get_id()

    def __get_id(self):
        self.id = "%08i" % Block.count
        Block.count += 1

    def parse_name(self, block_str):
        '''
            Gets the block name from block_str

            block_str is list of lines of form
            ----------------
            IN: 
            0x08000240:  2100       movs	r1, #0
            0x08000242:  e003       b.n	0x800024c

        '''
        return block_str[2].split(':')[0]


class Start_Block(Block):
    def __init__(self):
        self.block_str = None
        self.name = 'Start'
        self.id = 'Start'


class Stop_Block(Block):
    def __init__(self):
        self.block_str = None
        self.name = 'Stop'
        self.id = 'Stop'


def create_graph(filename, binary=None, export_named=None):
    '''
    Creates a two graphs that can be visulized with gephi,
    The first (*.graphml) has a only one node per block, and thus shows loops 
    and cycles
    the second (*.trace.graphml) is just a path and a node is created for every
    block in the trace
    Each node is a basic block and the edge are from previous block

    Count is number of time the edge has been called
    '''

    sym_lut = None
    if binary != None:
        from elf_sym_hal_getter import build_addr_to_sym_lookup
        sym_lut = build_addr_to_sym_lookup(binary)

    outfile_base = os.path.splitext(filename)[0]
    G = nx.DiGraph()
    P = nx.DiGraph()
    unique_blocks = {}
    with open(filename, 'rt') as infile:
        prev_block = Start_Block()
        block_str = []
        if export_named is not None and binary is not None:
            export_file = open(export_named, 'wt')
        else:
            export_file = 0
        for line in infile.readlines():

            block_str.append(line)
            if line == BLOCK_DELIMITER:
                block = Block(block_str, sym_lut)
                unique_blocks[block.addr] = block
                P.add_node(block.id, function=block.function,
                           addr=hex(block.addr))
                G.add_node(block.name, function=block.function,
                           addr=hex(block.addr))
                data = G.get_edge_data(prev_block.name, block.name)
                if data != None:
                    if data['weight'] < 10:
                        weight = data['weight'] + 1
                else:
                    weight = 1
                P.add_edge(prev_block.id, block.id)
                G.add_edge(prev_block.name, block.name, weight=weight)
                prev_block = block
                block_str = []
                if export_file:
                    l = line.strip('\n')
                    export_file.write("%s %s\n" % (l, block.function))
            else:
                if export_file:
                    export_file.write(line)

        stop = Stop_Block()
        P.add_edge(prev_block.id, stop.name)
        G.add_edge(prev_block.name, stop.name, weight=1)
        nx.write_graphml(G, outfile_base + '.graphml')
        nx.write_graphml(P, outfile_base + '.trace.graphml')
    return unique_blocks


def write_block_file(uniq_blocks, outfile):
    with open(outfile, 'wt') as out:
        out.write("Addr, Function\n")
        for addr, block in list(uniq_blocks.items()):
            out.write("%s,%s" % (hex(addr), block.function))


if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument("-f", '--file', required=True,
                   help='Output file from QEMU -d in_asm -D <file>')
    p.add_argument("-n", '--named', default=None,
                   help='Output file of QEMU log with function names added to each block')
    p.add_argument('-b', '--bin', required=False, default=None,
                   help=('Elf file to get symbols from. If provided will' +
                         ' attempt to map addresses to function names'))
    p.add_argument('-c', '--csv', required=False, default=None,
                   help='CSV File to write blocks to')

    args = p.parse_args()
    blocks = create_graph(args.file, args.bin, args.named)
    if args.csv is not None:
        write_block_file(blocks, args.csv)
    print(len(blocks))
