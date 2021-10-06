# HALucinator - Firmware rehosting through abstraction layer modeling.

NOTE: For a more recent version of HALucinator see https://github.com/halucinator

## Setup

Note:  This has been lightly tested on Ubuntu 16.04, and 18.04

1.  Install dependencies using `./install_deps.sh`

1.  Create and activate a python3 virtual environment (I use virtualmachine 
    wrapper but you can do this however you like)
    ```
       mkvirtualenv -p `which python3` halucinator
    ```
    If (halucinator) is not in your prompt use `workon halucinator`

    Note: On ubuntu 18.04 you may have to manually configure virtualenvwrapper. Or build you virtual environment using you preferred method
    ```bash
        pip3 install virtualenvwrapper
    ```
    Then add to `~/.bashrc` using your favorite editor and then run
    `source ~/.bashrc`.  Replace `your username` in below
    
    ```bash
    export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3
    export WORKON_HOME=$HOME/.virtualenvs
    export VIRTUALENVWRAPPER_VIRTUALENV=/home/<your username>/.local/bin/virtualenv
    source ~/.local/bin/virtualenvwrapper.sh
    ```

1.  Install Halucinator 
    Make sure you are in you virtual environment and then run
    ```
    pip install -r src/requirements.txt
    pip install -e src
    ```
1. Install Avatar's QEMU and GDB (Select avatar-qemu and gdb-arm)
   ```
   python -m avatar2.installer
   ```
   This step will take a while the first time, and you may have to make your terminal wider

1. Set environmental variable for HALUCINATOR_QEMU
  ```
    export HALUCINATOR_QEMU=`readlink -f ~/.avatar2/avatar-qemu/arm-softmmu/qemu-system-arm`
  ```

1.  Simlink gdb-multiarch to arm-none-eabi-gdb
    If you don't have arm-none-eabi-gdb on your path you can apt get it on Ubuntu 16.04.  On Ubuntu 18.04 you can use gdb-multiarch
    which was installed in step 1.  Just symlink it to `arm-none-eabi-gdb`

    ```bash
    sudo ln /usr/bin/gdb-multiarch /usr/bin/arm-none-eabi-gdb
    ```
    
### Note on setting HALUCINATOR_QEMU

If you use virtualenvwrapper as above you 
can set it up to be automatically set and removed when activating/deactivating
the virtual environment using the postactivate and predeactivate scripts below.
  
Contents of $VIRTUAL_ENV/bin/postactivate

```sh
export HALUCINATOR_QEMU=<full path to your qemu>
```

Contents of $VIRTUAL_ENV/bin/predeactivate

```sh
unset HALUCINATOR_QEMU
```

## Running

Running Halucinator requires a configuration file that lists the functions to 
intercept and the handler to be called on that interception. I usually split 
this config across three files for portability.  The files are a memory file that
describes the memory layout, an intercept file that describes what to intercept
and a symbol/address file that maps addresses to symbol names.  See the Config 
File section below for full details

All of these commands assume you are in your halucinator virtual environment

```sh
halucinator  -c=<memory_file.yaml> -c=<intercept_file.yaml> -c=<address_file.yaml>
```

## Running an Example

### Building STM MX Cube Examples

This has already been done for Uart example file below.

A tool to convert the STM's Software Workbench for STM (SW4STM) was developed to
enable compiling their IDE projects using make.
This has only been tested on a few STM32F4 examples from STM32Cube_F4_V1.21.0.
It compiles them as cortex-m3 devices and not cortex-m4 to enable easier 
emulation in QEMU. 

To use go into the directory below the SW4STM32 directory in the project and run
`python3 <halucinator_repo_root>/src/tools/stm_tools/build_scripts/CubeMX2Makefile.py .`
Enter a name for the board, and the applications. Then run `make all`.
The binary created will be in `bin` directory

Example

```bash
cd STM32Cube_FW_F4_V1.21.0/Projects/STM32469I_EVAL/Examples/UART/UART_HyperTerminal_IT/SW4STM32/STM32469I_EVAL
python3 <halucinator_repo_root>/src/tools/stm_tools/build_scripts/CubeMX2Makefile.py .
Board: STM32469I_Eval
APP: Uart_IT
make all
```


###  STM32F469I Uart Example

To give an idea how to use Halucinator an example is provided in `test/STM32/example`.

#### Setup
Note: This was done prior and the files are in the repo in `test/STM/example`. 
If you just want to run the example without building it just go to Running UART Example below.

This procedure should be followed for other binaries.
In list below after the colon (:) denotes the file/cmd .  

1. Compile binary as above
2. Copy binary to a dir of you choice and cd to it:  `test/STM32/example`
3. Create binary file: `<halucinator_repo_root>/src/tools/make_bin.sh Uart_Hyperterminal_IT_O0.elf` creates `Uart_Hyperterminal_IT_O0.elf.bin`
4. Create Memory Layout (specifies memory map of chip): `Uart_Hyperterminal_IT_O0_memory.yaml`
5. Create Address File (maps function names to address): `Uart_Hyperterminal_IT_O0_addrs.yaml`
6. Create Intercept File (defines functions to intercept and what handler to use for it): `Uart_Hyperterminal_IT_O0_config.yaml`
7. (Optional) create shell script to run it: `run.sh`

Note: Symbols used in the address file can be created from an elf file with symbols
using `hal_make_addrs` This requires installing angr in halucinator's virtual environment.
This was used to create `Uart_Hyperterminal_IT_O0_addrs.yaml`

To use it the first time you would. Install angr (e.g. `pip install angr` from
the halucinator virtual environment)

```sh
hal_make_addrs -b <path to elf file>
```

#### Running UART Example

Start the UART Peripheral device,  this a script that will subscribe to the Uart 
on the peripheral server and enable interacting with it.

```bash
hal_dev_uart -i=1073811456
```

In separate terminal start halucinator with the firmware.

```bash

<halucinator_repo_root>$ halucinator -c=test/STM32/example/Uart_Hyperterminal_IT_O0_config.yaml \
  -c=test/STM32/example/Uart_Hyperterminal_IT_O0_addrs.yaml \
  -c=test/STM32/example/Uart_Hyperterminal_IT_O0_memory.yaml --log_blocks -n Uart_Example

or
<halucinator_repo_root>& test/STM32/example/run.sh
```
Note the --log_blocks and -n are optional.

You will eventually see in both terminals messages containing
```
 ****UART-Hyperterminal communication based on IT ****
 Enter 10 characters using keyboard :
```

Enter 10 Characters in the first terminal running `hal_dev_uart` press enter
should then see text echoed followed.

```txt
 Example Finished
```

#### Stopping

Press `ctrl-c`. If for some reason this doesn't work kill it with `ctrl-z` 
and `kill %`, or `killall -9 halucinator`

Logs are kept in the `tmp/<value of -n option>`. e.g `tmp/Uart_Example/`

## Config file

How the emulation is performed is controlled by a yaml config file.  It is passed 
in using the -c flag, which can be repeated with the config files being appended
and the later files overwriting any collisions from previous file.  The config 
is specified as follows.  Default field values are in () and types are in <>

```yaml
machine:   # Optional, describes qemu machine used in avatar entry optional defaults in ()
           # if never specified default settings as below are used. 
  arch: (cortex-m3)<str>,
  cpu_model: (cortex-m3)<str>,
  entry_addr: (None)<int>,  # Initial value to pc reg. Obtained from 0x0000_0004
                        # of memory named init_mem if it exists else memory
                        # named flash
  init_sp: (None)<int>,     # Initial value for sp reg, Obtained from 0x0000_0000
                        # of memory named init_mem if it exists else memory
                        # named flash
  gdb_exe: ('arm-none-eabi-gdb')<path> # Path to gdb to use


memories:  #List of the memories to add to the machine
  - name: <str>,       # Required
    base_addr:  <int>, # Required
    size: <int>,       # Required
    perimissions: (rwx)<r--|rw-|r-x>, # Optional 
    file: filename<path>   # Optional Filename to populate memory with, use full path or
                      # path relative to this config file, blank memory used if not specified
    emulate: class<AvatarPeripheral subclass>    # Class to emulate memory 

peripherals:  # Optional, A list of memories, same as memories except emulate field required

intercepts:  # Optional, list of intercepts to place
  - class:  <BPHandler subclass>,  # Required use full import path
    function: <str>     # Required: Function name in @bp_handler([]) used to
                        #   determine class method used to handle this intercept
    symbol: (Value of function)<str>  # Optional, Symbol name use to determine 
                                      # address in firmware to intercept, name 
                                      # must be present in symbols,
                                      # If not use value of function is used
    addr: (from symbols)<int>  # Optional, Address of where to place this intercept,
                               # generally recommend not setting this value, but
                               # instead setting symbol and adding entry to
                               # symbols (in seperate file) as this makes config 
                               # files more portable. If set will take precidence over symbol
    class_args: ({})<dict>  # Optional dictionary of args to pass to class's
                       # __init__ method, keys are parameter names
    registration_args: ({})<dict>  # Optional: Arguments passed to register_handler
                                   # method when adding this method
    run_once: (false)<bool>   # Optional: Set to true if only want intercept to run once
    watchpoint: (false)<bool> # Optional: Set to true if this is a memory watch point

symbols:  # Optional, dictionary mapping addresses to symbol names, used to
          # determine addresses for symbol values in intercepts
  addr0<int>: symbol_name<str>
  addr1<int>: symbol1_name<str>

options: # Optional, Key:Value pairs you want accessible during emulation

```

The symbols in the config can also be specified using one or more symbols files
passed in using -s. This is a csv file each line defining a symbol as shown below

```csv
symbol_name<str>, start_addr<int>, last_addr<int>
```
