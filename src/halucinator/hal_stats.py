# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.

import yaml

stats = {}
_stats_file = None


def set_filename(filename):
    global _stats_file
    _stats_file = filename


def write_on_update(set_key, value):
    '''
        Writes the stats information when if value is added to the set in 
        the stats dictionary
    '''
    global stats
    if value not in stats[set_key]:
        stats[set_key].add(value)
        stats[set_key+'_length'] = len(stats[set_key])
        with open(_stats_file, 'w') as outfile:
            yaml.safe_dump(stats, outfile)
