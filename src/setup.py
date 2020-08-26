#!/usr/bin/env python

# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
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


setup(name='halucinator',
      version='1.0a',
      description='Emulation and rehosting framework',
      author='Abe Clements and Eric Gustafson',
      author_email='',
      # url='https://seclab.cs.ucsb.edu',
      packages=get_packages('halucinator'),
      entry_points ={'console_scripts': [
            'halucinator = halucinator.main:main',
            'qemulog2trace= tools.qemu_to_trace:main',
        ]},
      requires=['avatar2',
                'zeromq',
                'PyYAML',
                'IPython', ])
