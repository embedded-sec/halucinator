# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.


import yaml
from avatar2 import Avatar, QemuTarget, ARM_CORTEX_M3, TargetStates
from avatar2.peripherals.avatar_peripheral import AvatarPeripheral
import logging
import os
from .peripheral_models import generic as peripheral_emulators
from IPython import embed
#import gdbgui.backend as gdbgui
import time
import sys

from .util import hexyaml
#from . import bp_handlers
from .bp_handlers import intercepts as intercepts
from .peripheral_models import peripheral_server as periph_server
from .util.profile_hals import State_Recorder
from .util import cortex_m_helpers as CM_helpers
from . import hal_stats


log = logging.getLogger("Halucinator")
log.setLevel(logging.DEBUG)
avalog = logging.getLogger("avatar")
avalog.setLevel(logging.WARN)
pslog = logging.getLogger("PeripheralServer")
pslog.setLevel(logging.WARN)
# log.setLevel(logging.DEBUG)

PATCH_MEMORY_SIZE = 4096
INTERCEPT_RETURN_INSTR_ADDR = 0x20000000 - PATCH_MEMORY_SIZE


def add_patch_memory(avatar, qemu):
    ''' 
        Use a patch memory to return from intercepted functions, as 
        it allows tracking number of intercepts
    '''

    log.info("Adding Patch Memory %s:%i" %
             (hex(INTERCEPT_RETURN_INSTR_ADDR), PATCH_MEMORY_SIZE))
    avatar.add_memory_range(INTERCEPT_RETURN_INSTR_ADDR, PATCH_MEMORY_SIZE,
                            name='patch_memory', permissions='rwx')


def write_patch_memory(qemu):
    BXLR_ADDR = INTERCEPT_RETURN_INSTR_ADDR | 1
    CALL_RETURN_ZERO_ADDR = BXLR_ADDR + 2
    BXLR = 0x4770
    BXR0 = 0x4700
    BLXR0 = 0x4780
    MOVS_R0_0 = 0x0020
    POP_PC = 0x00BD

    qemu.write_memory(INTERCEPT_RETURN_INSTR_ADDR, 2, BXLR, 1)

    # Sets R0 to 0, then return to address on stack
    qemu.write_memory(CALL_RETURN_ZERO_ADDR, 2, MOVS_R0_0, 1)
    qemu.write_memory(CALL_RETURN_ZERO_ADDR+2, 2, POP_PC, 1)

    def exec_return(value=None):
        if value is not None:
            qemu.regs.r0 = value
        qemu.regs.pc = BXLR_ADDR
    qemu.exec_return = exec_return

    def write_bx_lr(addr):
        qemu.write_memory(addr, 2, BXLR, 1)
    qemu.write_bx_lr = write_bx_lr

    def write_bx_r0(addr):
        qemu.write_memory(addr, 2, BXR0, 1)
    qemu.write_bx_r0 = write_bx_r0

    def write_blx_r0(addr):
        qemu.write_memory(addr, 2, BLXR0, 1)
    qemu.write_blx_r0 = write_blx_r0

    def call_ret_0(callee, arg0):
        # Save LR
        sp = qemu.regs.sp - 4
        qemu.regs.sp = sp
        qemu.write_memory(sp, 4, qemu.regs.lr, 1)
        # Set return to out patch that will set R0 to 0
        qemu.regs.lr = CALL_RETURN_ZERO_ADDR
        qemu.regs.r0 = arg0
        qemu.regs.pc = callee
    qemu.call_ret_0 = call_ret_0


def find_qemu():
    default = "../../3rd_party/avatar-qemu/arm-softmmu/qemu-system-arm"
    real_path = os.path.realpath(os.path.join(
        os.path.dirname(__file__), default))
    if not os.path.exists(real_path):
        print(("ERROR: Could not find qemu in %s did you build it?" % real_path))
        exit(1)
    else:
        print(("Found qemu in %s" % real_path))
    return real_path


#  Add Interrupt support to QemuTarget, will eventually be in Avatar
#  So until then just hack in a patch like this
def trigger_interrupt(qemu, interrupt_number, cpu_number=0):
    qemu.protocols.monitor.execute_command(
        'avatar-armv7m-inject-irq',
        {'num_irq': interrupt_number, 'num_cpu': cpu_number})


def set_vector_table_base(qemu, base, cpu_number=0):
    qemu.protocols.monitor.execute_command(
        'avatar-armv7m-set-vector-table-base',
        {'base': base, 'num_cpu': cpu_number})


def enable_interrupt(qemu, interrupt_number, cpu_number=0):
    qemu.protocols.monitor.execute_command(
        'avatar-armv7m-enable-irq',
        {'num_irq': interrupt_number, 'num_cpu': cpu_number})


QemuTarget.trigger_interrupt = trigger_interrupt
QemuTarget.set_vector_table_base = set_vector_table_base
# --------------------------END QemuTarget Hack --------------------------------


def get_qemu_target(name, entry_addr, firmware=None, log_basic_blocks=False,
                    output_base_dir='', gdb_port=1234):
    qemu_path = find_qemu()
    outdir = os.path.join(output_base_dir, 'tmp', name)
    hal_stats.set_filename(outdir+"/stats.yaml")
    avatar = Avatar(arch=ARM_CORTEX_M3, output_directory=outdir)
    print(("GDB_PORT", gdb_port))
    log.critical("Using qemu in %s" % qemu_path)
    qemu = avatar.add_target(QemuTarget,
                             gdb_executable="arm-none-eabi-gdb",
                             gdb_port=gdb_port,
                             qmp_port=gdb_port+1,
                             firmware=firmware,
                             executable=qemu_path,
                             entry_address=entry_addr, name=name)
    # qemu.log.setLevel(logging.DEBUG)

    if log_basic_blocks == 'irq':
        qemu.additional_args = ['-d', 'in_asm,exec,int,cpu,guest_errors,avatar,trace:nvic*', '-D',
                                os.path.join(outdir, 'qemu_asm.log')]
    elif log_basic_blocks:
        qemu.additional_args = ['-d', 'in_asm', '-D',
                                os.path.join(outdir, 'qemu_asm.log')]
    return avatar, qemu


def setup_peripheral(avatar, name, per, base_dir=None):
    '''
        Just a memory, but will usually have an emulate field. 
        May not when just want to treat peripheral as a memory
    '''
    setup_memory(avatar, name, per, base_dir)


def get_memory_filename(memory, base_dir):
    '''
    Gets the filename for the memory to load into memory
    Args:
        memory(dict): Dict from yaml config file for memory 
                          requires keys [base_addr, size] 
                          optional keys [emulate (a memory emulator), 
                          perimissions, filename]

    '''
    filename = memory['file'] if 'file' in memory else None
    if filename != None:
        if base_dir != None and not os.path.isabs(filename):
            filename = os.path.join(base_dir, filename)
    return filename


def setup_memory(avatar, name, memory, base_dir=None, record_memories=None):
    '''
        Sets up memory regions for the emualted devices
        Args:
            avatar(Avatar):
            name(str):    Name for the memory
            memory(dict): Dict from yaml config file for memory 
                          requires keys [base_addr, size] 
                          optional keys [emulate (a memory emulator), 
                          perimissions, filename]
            returns:
                permission
    '''

    filename = get_memory_filename(memory, base_dir)

    permissions = memory['permissions'] if 'permissions' in memory else 'rwx'
    # if 'model' in memory:
    #     emulate = getattr(peripheral_emulators, memory['emulate'])
    # #TODO, just move this to models/bp_handlers but don't want break
    # all configs right now
    if 'emulate' in memory:
        emulate = getattr(peripheral_emulators, memory['emulate'])
    else:
        emulate = None
    log.info("Adding Memory: %s Addr: 0x%08x Size: 0x%08x" %
             (name, memory['base_addr'], memory['size']))
    avatar.add_memory_range(memory['base_addr'], memory['size'],
                            name=name, file=filename,
                            permissions=permissions, emulate=emulate)

    if record_memories is not None:
        if 'w' in permissions:
            record_memories.append((memory['base_addr'], memory['size']))


def get_entry_and_init_sp(config, base_dir):
    '''
    Gets the entry point and the initial SP.
    This is a work around because AVATAR-QEMU does not init Cortex-M3
    correctly. 

    Works by identifying the init_memory, and reading the reset vector from
    the file loaded into it memory.
    Args:
        config(dict):   Dictionary of config file(yaml)
    avatar.add_memory_range(0xB000_00000, memory['size'], 
                            name=name, file=filename, 
                            permissions=permissions, emulate=emulate)
    avatar.add_memory_range(0xB000_00000, memory['size'], 
                            name=name, file=filename, 
                            permissions=permissions, emulate=emulate)ion
    avatar.add_memory_range(0xB000_00000, memory['size'], 
                            name=name, file=filename, 
                            permissions=permissions, emulate=emulate)ointer
    avatar.add_memory_range(0xB000_00000, memory['size'], 
                            name=name, file=filename, 
                            permissions=permissions, emulate=emulate)
    '''

    init_memory = config['init_memory'] if 'init_memory' in config else 'flash'
    init_filename = get_memory_filename(
        config['memories'][init_memory], base_dir)

    init_sp, entry_addr, = CM_helpers.get_sp_and_entry(init_filename)
    return init_sp, entry_addr


def emulate_binary(config, base_dir, target_name=None, log_basic_blocks=None,
                   rx_port=5555, tx_port=5556, gdb_port=1234, elf_file=None, db_name=None):

    init_sp, entry_addr = get_entry_and_init_sp(config, base_dir)
    periph_server.base_dir = base_dir
    log.info("Entry Addr: 0x%08x,  Init_SP 0x%08x" % (entry_addr, init_sp))

    avatar, qemu = get_qemu_target(target_name, entry_addr,
                                   log_basic_blocks=log_basic_blocks,
                                   output_base_dir=base_dir, gdb_port=gdb_port)

    if 'options' in config:
        log.info("Config file has options")
        if 'remove_bitband' in config['options'] and \
                config['options']['remove_bitband']:
            log.info("Removing Bitband")
            qemu.remove_bitband = True

    # Setup Memory Regions
    record_memories = []
    for name, memory in list(config['memories'].items()):
        setup_memory(avatar, name, memory, base_dir, record_memories)

    # Add memory needed for returns
    add_patch_memory(avatar, qemu)

    # Add recorder to avatar
    # Used for debugging peripherals
    if elf_file is not None:
        if db_name is None:
            db_name = ".".join((os.path.splitext(elf_file)[
                               0], str(target_name), "sqlite"))
        avatar.recorder = State_Recorder(
            db_name, qemu, record_memories, elf_file)
    else:
        avatar.recorder = None

    # Setup Peripherals Regions
    for name, per in list(config['peripherals'].items()):
        # They are just memories
        setup_peripheral(avatar, name, per, base_dir)

    # Setup Intercept MMIO Regions
    added_classes = []
    for intercept in config['intercepts']:
        bp_cls = intercepts.get_bp_handler(intercept)
        if issubclass(bp_cls.__class__, AvatarPeripheral):
            name, addr, size, per = bp_cls.get_mmio_info()
            if bp_cls not in added_classes:
                log.info("Adding Memory Region for %s, (Name: %s, Addr: %s, Size:%s)"
                         % (bp_cls.__class__.__name__, name, hex(addr), hex(size)))
                avatar.add_memory_range(addr, size, name=name, permissions=per,
                                        forwarded=True, forwarded_to=bp_cls)
                added_classes.append(bp_cls)
   # Setup Intecepts
    avatar.watchmen.add_watchman('BreakpointHit', 'before',
                                 intercepts.interceptor, is_async=True)
    qemu.gdb_port = gdb_port

    avatar.callables = config['callables']
    avatar.init_targets()

    for intercept in config['intercepts']:
        intercepts.register_bp_handler(qemu, intercept)

    # Work around Avatar-QEMU's improper init of Cortex-M3
    qemu.regs.cpsr |= 0x20  # Make sure the thumb bit is set
    qemu.regs.sp = init_sp  # Set SP as Qemu doesn't init correctly
    # TODO Change to be read from config
    qemu.set_vector_table_base(0x08000000)
    write_patch_memory(qemu)

    # Emulate the Binary
    periph_server.start(rx_port, tx_port, qemu)
    # import os; os.system('stty sane') # Make so display works
    # import IPython; IPython.embed()
    qemu.cont()

    try:
        periph_server.run_server()
        # while 1:

        #    time.sleep(0.5)
    except KeyboardInterrupt:
        # import os; os.system('stty sane') # Make so display works
        # import IPython; IPython.embed()
        periph_server.stop()
        avatar.stop()
        avatar.shutdown()
        quit(-1)


def override_addresses(config, address_file):
    '''
        Replaces address in config with address from the address_file with same
        function name
    '''
    with open(address_file, 'rb') as infile:
        addr_config = yaml.load(infile, Loader=yaml.FullLoader)
        addr2func_lut = addr_config['symbols']
        func2addr_lut = {}
        for key, val in list(addr2func_lut.items()):
            func2addr_lut[val] = key
        base_addr = addr_config['base_address']
        entry_addr = addr_config['entry_point']

    remove_ids = []
    for intercept in config['intercepts']:
        f_name = intercept['function']
        # Update address if in address list
        if f_name in func2addr_lut:
            intercept['addr'] = (func2addr_lut[f_name] &
                                 0xFFFFFFFE)  # clear thumb bit
            log.info("Replacing address for %s with %s " %
                     (f_name, hex(func2addr_lut[f_name])))
        elif 'addr' not in intercept:
            remove_ids.append((intercept, f_name))

    config['callables'] = func2addr_lut

    for (intercept, f_name) in remove_ids:
        log.info("Removing Intercept for: %s" % f_name)
        config['intercepts'].remove(intercept)

    return base_addr, entry_addr


if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('-c', '--config', required=True,
                   help='Config file used to run emulation')
    p.add_argument('-m', '--memory_config', required=False, default=None,
                   help='Memory Config, will overwrite config in --config if present if memories not in -c this is required')
    p.add_argument('-a', '--address', required=False,
                   help='Yaml file of function addresses, providing it over' +
                   'rides addresses in config file for functions')
    p.add_argument('--log_blocks', default=False, const=True, nargs='?',
                   help="Enables QEMU's logging of basic blocks, options [irq]")
    p.add_argument('-n', '--name', default='HALucinator',
                   help='Name of target for avatar, used for logging')
    p.add_argument('-r', '--rx_port', default=5555, type=int,
                   help='Port number to receive zmq messages for IO on')
    p.add_argument('-t', '--tx_port', default=5556, type=int,
                   help='Port number to send IO messages via zmq')
    p.add_argument('-p', '--gdb_port', default=1234, type=int,
                   help="GDB_Port")
    p.add_argument('-e', '--elf', default=None,
                   help='Elf file, required to use recorder')

    args = p.parse_args()

    logging.basicConfig()
    log = logging.getLogger()
    # log.setLevel(logging.INFO)
    with open(args.config, 'rb') as infile:
        config = yaml.load(infile, Loader=yaml.FullLoader)

    if args.address is not None:
        override_addresses(config, args.address)

    if 'memories' not in config and args.memory_config == None:
        print("Memory Configuration must be in config file or provided using -m")
        p.print_usage()
        quit(-1)

    if args.memory_config:
        # Use memory configuration from mem_config
        base_dir = os.path.split(args.memory_config)[0]
        with open(args.memory_config, 'rb') as infile:
            mem_config = yaml.load(infile, Loader=yaml.FullLoader)
            if 'options' in mem_config:
                config['options'] = mem_config['options']
            config['memories'] = mem_config['memories']
            config['peripherals'] = mem_config['peripherals']
    else:
        base_dir = os.path.split(args.config)[0]

    emulate_binary(config, base_dir, args.name, args.log_blocks,
                   args.rx_port, args.tx_port,
                   elf_file=args.elf, gdb_port=args.gdb_port)
