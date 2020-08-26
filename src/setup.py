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
      version='1.0.5',
      description='Firmware emulation and rehosting framework',
      author='Abe Clements and Eric Gustafson',
      packages=get_packages('halucinator'),
      entry_points ={'console_scripts': [
            'halucinator = halucinator.main:main',
            'qemulog2trace = tools.qemu_to_trace:main',
            'hal_make_addr= halucinator.util.elf_sym_hal_getter:main',
            'hal_dev_uart=halucinator.external_devices.uart:main',
            'hal_dev_virt_hub=halucinator.external_devices.ethernet_virt_hub:main',
            'hal_dev_eth_wireless=halucinator.external_devices.ethernet_wireless:main',
            'hal_dev_host_eth=halucinator.external_devices.host_ethernet:main',
            'hal_dev_host_eth_server=halucinator.external_devices.host_ethernet_server:main',
            'hal_dev_802_15_4=halucinator.external_devices.IEEE802_15_4:main',
            'hal_dev_irq_trigger=halucinator.external_devices.trigger_interrupt:main'
        ]},
      requires=['avatar2',    
                'zeromq',
                'PyYAML',
                'IPython' ])
