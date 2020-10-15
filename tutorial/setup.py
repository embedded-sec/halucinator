#!/usr/bin/env python

# Copyright 2020 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.


import os
from distutils.core import setup


def get_packages(rel_dir):
    packages = [rel_dir]
    for x in os.walk(rel_dir):
        # break into parts
        base = list(os.path.split(x[0]))
        if base[0] == "":
            del base[0]

        for mod_name in x[1]:
            packages.append(".".join(base + [mod_name]))

    return packages


setup(name='hal_tutorial',
      version='0.0.1',
      description='Halucinator Tutorial',
      author='<Your Name Here>',
      packages=get_packages('hal_tutorial'),
      entry_points ={'console_scripts': [
            'my_led_device = hal_tutorial.external_devices.led_external_device:main'
        ]},
      requires=['halucinator'])
