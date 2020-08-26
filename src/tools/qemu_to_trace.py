#!/usr/bin/python3

import argparse
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("logfile", help="qemu log file containing block trace")
    parser.add_argument("-o", dest='file', default=None, 
        help="FILE: File to write trace to should have .addrlist extension")
    args = parser.parse_args()

    with open(args.logfile, 'r') as fin:
        addrs = list()
        while True:
            line = fin.readline()
            if not line:
                break
            if line == 'IN: \n':
                line = fin.readline()
                if line.startswith('0x'):
                    pair = [int(line.split()[0][2:-1], 16), int(line.split()[0][2:-1], 16)]
                    while True:
                        line = fin.readline()
                        if line == '\n':
                            break
                        if line.startswith('0x'):
                            pair[1] = int(line.split()[0][2:-1], 16)
                addrs.append(pair)
        if args.file == None:
            args.file = os.path.splitext(args.logfile)[0] +'.addrlist'
        with open(args.file, 'w') as fout:
                fout.write('{}'.format('\n'.join('[{}]'.format(', '.join(format(x, '08x') for x in pair)) for pair in addrs)))
    

if __name__ == "__main__":
    main()
