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

## Running an Example

### Building STM MX Cube Examples

This has already been done for Uart example file below.

A tool to convert the STM's Software Workbench for STM (SW4STM) was developed to
enable compiling their IDE projects using make.
This has only been tested on a few STM32F4 examples from STM32Cube_F4_V1.21.0.
It compile them as cortex-m3 devices and not cortex-m4 to enable easier 
emulation in QEMU. 

To use go into the directory below the SW4STM32 directory in the project and run
`<halucinator_repo_root>/src/tools/stm_tools/build_scripts/CubeMX2Makefile.py .`
Enter a name for the board, and the applications. Then run `make all`.
The binary created will be in `bin` directory

Example

```bash
cd STM32Cube_FW_F4_V1.21.0/Projects/STM32469I_EVAL/Examples/UART/UART_HyperTerminal_IT/SW4STM32/STM32469I_EVAL
<halucinator_repo_root>/src/tools/stm_tools/build_scripts/CubeMX2Makefile.py .
Board: STM32469I_Eval
APP: Uart_IT
make all
```


###  STM32F469I Uart Example

To give an idea how to use Halucinator an example is provided in `test/STM32/example`.

#### Setup
Note: This was done prior and the files are in the repo in `test/STM/example`.
This procedure should be followed for other binaries.
In list below after the colon (:) denotes the file/cmd .  

1. Compile binary as above
2. Copy binary to a dir of you choice and cd to it:  `test/STM32/example`
3. Create binary file: `<halucinator_repo_root>/src/tools/make_bin.sh Uart_Hyperterminal_IT_O0.elf` creates `Uart_Hyperterminal_IT_O0.elf.bin`
4. Create Memory Layout (specifies memory map of chip): `Uart_Hyperterminal_IT_O0_memory.yaml`
5. Create Address File (maps function names to address): `Uart_Hyperterminal_IT_O0_addrs.yaml`
6. Create Config File (defines functions to intercept and what handler to use for it): `Uart_Hyperterminal_IT_O0_config.yaml`
7. (Optional) create shell script to run it: `run.sh`

Note: the Memory file can be created using `src/halucinator/util/elf_sym_hal_getter.py` 
from an elf with symbols.  This requires angr and pyyaml.
This was used to create `Uart_Hyperterminal_IT_O0_addrs`


#### Running

Start the UART Peripheral device,  this a script that will subscribe to the Uart on the peripheral server and
enable interacting with it.

```bash
workon halucinator
<halucinator_repo_root>$python -m halucinator.external_devices.uart -i=1073811456

```

In separate terminal start halucinator with the firmware.

```bash
workon halucinator
<halucinator_repo_root>$./halucinator -c=test/STM32/example/Uart_Hyperterminal_IT_O0_config.yaml \
  -a=test/STM32/example/Uart_Hyperterminal_IT_O0_addr.yaml \
  -m=test/STM32/example/Uart_Hyperterminal_IT_O0_memory.yaml --log_blocks -n Uart_Example

or
<halucinator_repo_root>$test/STM32/example/run.sh 
```
Note the --log_blocks and -n are optional.

You will eventually see in both terminals messages containing
```
 ****UART-Hyperterminal communication based on IT ****
 Enter 10 characters using keyboard :
```

Enter 10 Characters in the first terminal running the uart external device and press enter
should then see below in halucinator terminal
```
INFO:STM32F4UART:Waiting for data: 10
INFO:STM32F4UART:Got Data: 1342154134
INFO:STM32F4UART:Get State
INFO:STM32F4UART:Writing: 1342154134
INFO:STM32F4UART:Get State
INFO:STM32F4UART:Writing:
 Example Finished

```

#### Stopping

Avatar creates many threads and std input gets sent to QEMU thus killing it is not trivial. 
I usually have to kill it with `ctrl-z` and `kill %`

Logs are kept in the `<directory of the config file>/tmp/<value of -n option`. e.g `test/STM32/example/tmp/Uart_Example/`

## TODOs
Document what is in config file, address files, and memory files
