# HALucinator - Firmware rehosting through abstraction layer modeling.

## Prerequisites

```
apt install pkg-config build-essential zlib1g-dev pkg-config libglib2.0-dev binutils-dev libboost-all-dev autoconf libtool libssl-dev libpixman-1-dev libpython-dev python-pip python-capstone virtualenv gcc-arm-none-eabi
pip install virtualenv virtualenvwrapper
```

## Setup

Run the setup.sh script. This will install dependencies, and create a 
python virtual environment named halucinator.

Tested on Ubuntu 16.04
```
setup.sh
```

Build QEMU used by HALucinator
```
cd 
./build_qemu.sh
```

## Running

Running Halucinator requires a configuration file that lists the functions to 
intercept and the handler to be called on that interception. It also requires
and address file linking addresses to function names, and a memory file that 
describes the memory layout of the system being emulated.  The firmware file is 
specified in the memory file.

Examples of these files are given in the test directoy.

```
workon halucinator
./halucinator -c=<config_file.yaml> -a=<address_file.yaml> -m=<memory_file.yaml>
```
