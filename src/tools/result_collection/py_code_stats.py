# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. 
# Government retains certain rights in this software.

import radon
from radon.cli import Config
import radon.complexity as cc_mod
from radon.cli.harvest import CCHarvester, RawHarvester
import math
import numpy as np
from tabulate import tabulate
import csv

cc_config = Config(
    order=getattr(cc_mod, 'SCORE'),
    no_assert=False,
    min='A',
    max='F',
    show_complexity=True,
    show_closures=False,
    average=True,
    total_average=False,
    exclude = ['*.pyc'],
    ignore = [""]
)

def get_stats(paths):
    cc = CCHarvester(paths, cc_config)
    raw = RawHarvester(paths, cc_config)
    cc.run()
    raw.run()
    
    header = ['Filename', "SLOC", '#Functions', '#Intercepts', 'Max CC', 
              'Ave CC', 'Median CC', 'Min CC']
    data = {}
    for file_data in cc.results:
        filename, cc_results = file_data
        complexity = [x.complexity for x in cc_results if hasattr(x, 'is_method') and x.is_method]
        if len(complexity) > 0:
            print "Getting Complexity for:", filename
            data[filename] = {}
            data[filename]['Filename'] = filename
            data[filename]['Max CC'] = max(complexity)
            data[filename]['Min CC'] = min(complexity)
            data[filename]['Med CC'] = np.median(complexity)
            data[filename]['Ave CC'] = np.mean(complexity)
            data[filename]['#Functions'] = len(complexity)
        else:
            print "Skipping ", filename

    for file_data in raw.results:
        filename, results = file_data
        if filename in data:
            data[filename]['SLOC'] = results['sloc']
        else:
            print "Skipping ", filename

    return data

def write_csv(data, header, outfile):
    with open(outfile, 'wb') as csv_out:
        writer = csv.writer(csv_out)
        writer.writerow(header)
        for row in data:
            writer.writerow(row)

if __name__ == "__main__":
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument("-p", "--paths", required=True,
                    help="Paths to parse")
    p.add_argument("-o", "--outfile", default='static_stats.csv',
                    help="File to save results to")

    
    args = p.parse_args()
    stats = get_stats(args.paths)

    headers = ['Filename', "SLOC", '#Functions', 'Max CC', 
              'Ave CC', 'Med CC', 'Min CC']
    data = []
    for filename, d in stats.items():
        data.append( [d[h] for h in headers]) # flip the code and name and sort
    print(tabulate(data, headers=headers))
    write_csv(data, headers, args.outfile)


