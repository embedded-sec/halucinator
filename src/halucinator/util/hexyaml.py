# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC 
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a 
# non-exclusive license for use of this work by or on behalf of the U.S. 
# Government. Export of this data may require a license from the United States 
# Government.

import yaml
'''
    Import this file and yaml to change yaml's default integer writing to hex
    Useage:
    import hexyaml
    import yaml

    use yaml as normal
'''

def hexint_presenter(dumper, data):
    return dumper.represent_int(hex(data))

yaml.add_representer(int, hexint_presenter)
