# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC 
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a 
# non-exclusive license for use of this work by or on behalf of the U.S. 
# Government. Export of this data may require a license from the United States 
# Government.

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
        with open(_stats_file, 'wb') as outfile:
            yaml.safe_dump(stats, outfile)