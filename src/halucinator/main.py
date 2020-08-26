# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.

import yaml
from avatar2 import Avatar, QemuTarget, ARM_CORTEX_M3, ARM, TargetStates
from .qemu_targets import ARMQemuTarget, ARMv7mQemuTarget
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
from . import hal_log, hal_config
import signal
log = logging.getLogger(__name__)
hal_log.setLogConfig()



PATCH_MEMORY_SIZE = 4096
INTERCEPT_RETURN_INSTR_ADDR = 0x20000000 - PATCH_MEMORY_SIZE
ARCH_LUT={'cortex-m3': ARM_CORTEX_M3, 'arm': ARM}
QEMU_ARCH_LUT={'cortex-m3': ARMv7mQemuTarget, 'arm': ARMQemuTarget}


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
    '''
    Tries to find a valid Avatar-QEMU build to use for emulation
    Will use Environment Variable "HALUCINATOR_QEMU" as first choice
    then fall back to 
    <halucinator-root>/deps/avatar2/target/build/qemu/arm-softmmu/qemu-system-arm, 
    and then <halucinator-root>/deps/avatar2/targets/build/qemu/aarch64-softmmu/qemu-system-aarch64
        
    '''
    default = "../../deps/avatar2/target/build/qemu/arm-softmmu/qemu-system-arm"
    aarch64 = "../../deps/avatar2/targets/build/qemu/aarch64-softmmu/qemu-system-aarch64"
    default_path = os.path.realpath(os.path.join(
        os.path.dirname(__file__), default))
    aarch64_path = os.path.realpath(os.path.join(
        os.path.dirname(__file__), aarch64))

    if os.environ.get("HALUCINATOR_QEMU") is not None:
        if not os.path.exists(os.environ.get("HALUCINATOR_QEMU")):
            log.error('Path of "$HALUCINATOR_QEMU" is invalid"')
            exit(1)
        return os.environ.get("HALUCINATOR_QEMU")

    if os.path.exists(default_path):
        return default_path
    elif os.path.exists(aarch64_path):
        return aarch64_path
    log.error("QEMU NOT FOUND.\n Set environment variable $HALUCINATOR_QEMU to  full path of avatar-qemu binary")
    exit(1)


def get_qemu_target(name, config, firmware=None, log_basic_blocks=False, gdb_port=1234):
    qemu_path = find_qemu()
    outdir = os.path.join('tmp', name)
    hal_stats.set_filename(outdir+"/stats.yaml")
    
    # Get info from config
    arch = ARCH_LUT[config.machine.arch]
    
    avatar = Avatar(arch=arch, output_directory=outdir)
    log.info("GDB_PORT: %s"% gdb_port)
    log.info("QEMU Path: %s" % qemu_path)

    qemu_target = QEMU_ARCH_LUT[config.machine.arch]
    qemu = avatar.add_target(qemu_target,
                             cpu_model=config.machine.cpu_model,
                             gdb_executable=config.machine.gdb_exe,
                             gdb_port=gdb_port,
                             qmp_port=gdb_port+1,
                             firmware=firmware,
                             executable=qemu_path,
                             entry_address=config.machine.entry_addr, name=name)

    if log_basic_blocks == 'irq':
        qemu.additional_args = ['-d', 'in_asm,exec,int,cpu,guest_errors,avatar,trace:nvic*', '-D',
                                os.path.join(outdir, 'qemu_asm.log')]
    elif log_basic_blocks == 'regs':
        qemu.additional_args = ['-d', 'in_asm,exec,cpu', '-D',
                                os.path.join(outdir, 'qemu_asm.log')]
    elif log_basic_blocks == 'exec':
        qemu.additional_args = ['-d', 'exec', '-D',
                                os.path.join(outdir, 'qemu_asm.log')]
    elif log_basic_blocks == 'trace-nochain':
        qemu.additional_args = ['-d', 'in_asm,exec,nochain', '-D',
                                os.path.join(outdir, 'qemu_asm.log')]
    elif log_basic_blocks == 'trace':
        qemu.additional_args = ['-d', 'in_asm,exec', '-D',
                                os.path.join(outdir, 'qemu_asm.log')]

    elif log_basic_blocks:
        qemu.additional_args = ['-d', 'in_asm', '-D',
                                os.path.join(outdir, 'qemu_asm.log')]
    return avatar, qemu


def setup_memory(avatar, memory, record_memories=None):
    '''
        Sets up memory regions for the emualted devices
        Args:
            avatar(Avatar):
            name(str):    Name for the memory
            memory(HALMemoryConfigdict): 
    '''
    if memory.emulate is not None:
        emulate = getattr(peripheral_emulators, memory.emulate)
    else:
        emulate = None
    log.info("Adding Memory: %s Addr: 0x%08x Size: 0x%08x" %
             (memory.name, memory.base_addr, memory.size))
    avatar.add_memory_range(memory.base_addr, memory.size,
                            name=memory.name, file=memory.file,
                            permissions=memory.permissions, emulate=emulate)

    if record_memories is not None:
        if 'w' in memory.permissions:
            record_memories.append((memory.base_addr, memory.size))


def emulate_binary(config, target_name=None, log_basic_blocks=None,
                   rx_port=5555, tx_port=5556, gdb_port=1234, elf_file=None, db_name=None):

    # Bug in QEMU about init stack pointer/entry point this works around
    if config.machine.arch == 'cortex-m3':
        mem = config.memories['init_mem'] if 'init_mem' in config.memories else config.memories['flash']
        if mem is not None and mem.file is not None:
            config.machine.init_sp, entry_addr = CM_helpers.get_sp_and_entry(mem.file)
        # Only use the discoved entry point if one not explicitly set
        if config.machine.entry_addr is None:
            config.machine.entry_addr = entry_addr

    avatar, qemu = get_qemu_target(target_name, config,
                                   log_basic_blocks=log_basic_blocks,
                                   gdb_port=gdb_port)

    if 'remove_bitband' in config.options and config.options['remove_bitband']:
        log.info("Removing Bitband")
        qemu.remove_bitband = True

    # Setup Memory Regions
    record_memories = []
    for memory in config.memories.values():
        setup_memory(avatar, memory, record_memories)

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

    added_classes = []
    for intercept in config.intercepts:
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
    # Avatar may not support WatchPoints
    try:
        avatar.watchmen.add_watchman('WatchpointHit', 'before',
                                 intercepts.interceptor, is_async=True)
    except Exception as e:  #Avatar should really raise some specific types
        if e.args[0] == 'Requested event_type does not exist':
            log.warning("Watchpoints not supported")
        else:
            raise e

    qemu.gdb_port = gdb_port
    avatar.config = config
    log.info("Initializing Avatar Targets")
    avatar.init_targets()

    for intercept in config.intercepts:
        if intercept.bp_addr is not None:
            log.info("Registering Intercept: %s" % intercept)
            intercepts.register_bp_handler(qemu, intercept)


    # Work around Avatar-QEMU's improper init of Cortex-M3
    if config.machine.arch == 'cortex-m3':
        qemu.regs.cpsr |= 0x20  # Make sure the thumb bit is set
        qemu.regs.sp = config.machine.init_sp  # Set SP as Qemu doesn't init correctly
        qemu.set_vector_table_base(config.machine.vector_base)
    

    # Emulate the Binary
    periph_server.start(rx_port, tx_port, qemu)
    # import os; os.system('stty sane') # Make so display works
    # import IPython; IPython.embed()

    def signal_handler(signal, frame):
        print('You pressed Ctrl+C!')
        avatar.stop()
        avatar.shutdown()
        periph_server.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    log.info("Letting QEMU Run")
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


def main():
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('-c', '--config', action='append', required=True,
                   help='Config file(s) used to run emulation files are essentially'\
                   'appended to each other with later files taking precidence')
    # p.add_argument('-m', '--memory_config', required=False, default=None,
    #                help='Memory Config, will overwrite config in --config if present if memories not in -c this is required')
    p.add_argument('-s', '--symbols', action='append', default=[], 
                    help='CSV file with each row having symbol, first_addr, last_addr')
    p.add_argument('--log_blocks', default=False, const=True, nargs='?',
                   help="Enables QEMU's logging of basic blocks, options [irq,regs]")
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

    # Build configuration
    config = hal_config.HalucinatorConfig()
    for conf_file in args.config:
        log.info("Parsing config file: %s" %conf_file)
        config.add_yaml(conf_file)

    for csv_file in args.symbols:
        log.info("Parsing csv symbol file: %s" %csv_file)
        config.add_csv_symbols(csv_file)

    if not config.prepare_and_validate():
        log.error("Config invalid")
        exit(-1)

    emulate_binary(config, args.name, args.log_blocks,
                   args.rx_port, args.tx_port,
                   elf_file=args.elf, gdb_port=args.gdb_port)


if __name__ == '__main__':
    main()