import yaml
import logging
import os
from . import hal_log as hal_log_conf
import importlib
import inspect
import csv

log = logging.getLogger(__name__)
hal_log = hal_log_conf.getHalLogger()


class HalMemConfig(object):
    def __init__(self, name, config_filename, base_addr, size, permissions='rwx', file=None, emulate=None):
        '''
            Reads in config
        '''
        self.name = name
        self.config_file = config_filename # For reporting where problems are
        self.file = file
        self.size = size
        self.permissions = permissions
        self.emulate = emulate
        self.emulate_required = False
        self.base_addr = base_addr

        if self.file != None:
            self.get_full_path()
        
    def get_full_path(self):
        '''
            This make the file used by a memory relative to the config file
            containing it
        '''
        base_dir = os.path.dirname(self.config_file)
        if base_dir != None and not os.path.isabs(self.file):
            self.file = os.path.join(base_dir, self.file)

    def overlaps(self, other_mem):
        if  base_addr >= other_mem.base_addr and \
            self.base_addr < other_mem.base_addr+ other_mem.size:
            return True

        elif other.base_addr >= self.base_addr and \
            other.base_addr < self.base_addr+ self.size:
            return True
        return False

    def is_valid(self):
        valid = True
        if self.size %(4096) != 0:
            hal_log.error("Memory/Peripheral: has invalid size, must be multiple of 4kB\n\t%s" % self)
            valid = False

        if self.emulate_required and self.emulate is None:
            hal_log.error("Memory/Peripheral: requires emulate field\n\t%s" % self)
            valid = False
        return valid

    def __repr__(self):
        return "(%s){name:%s, base_addr:%#x, size:%#x, emulate:%s}" % \
          (self.config_file, self.name, self.base_addr, self.size, self.emulate)


class HalInterceptConfig(object):

    def __init__(self, config_file, cls, function, addr=None, symbol=None,
                 class_args=None, registration_args=None,
                 run_once=False, watchpoint=False):
        self.config_file = config_file
        self.symbol = symbol
        
        self.bp_addr = addr
        
        self.cls = cls
        self.function = function
        self.class_args = class_args if class_args is not None else {}
        if 'self' in self.class_args:
            del self.class_args['self']
        self.registration_args = registration_args if registration_args is not None else {}
        if 'self' in self.registration_args:
            del self.registration_args['self']
        self.run_once = run_once
        self.watchpoint = watchpoint  # Valid 'r', 'w' ,'rw'


    def _check_handler_is_valid(self):

        valid = True
        split_str = self.cls.split('.')
        module_str = ".".join(split_str[:-1])
        class_str = split_str[-1]
        try:
            module = importlib.import_module(module_str)
        except ImportError as e:
            hal_log.error("No module %s on Intercept %s"%(module_str, self))
            return False

        cls_obj = getattr(module, class_str, None)
        if cls_obj is None:
            hal_log.error("Intercept No Class for %s" % self)
            return False

        # See if could init class
        argspec = inspect.getargspec(cls_obj.__init__)
        if not set(self.class_args).issubset(set(argspec.args)):
            hal_log.error("class_arg are invalid for %s" % self)
            hal_log.error("    Valid options %s" % argspec.args)
            hal_log.error("    Input options %s" % self.class_args)
            valid = False

        argspec = inspect.getargspec(cls_obj.register_handler)
        if not set(self.registration_args).issubset(set(argspec.args)):
            hal_log.error("class_arg are invalid for %s" % self)
            hal_log.error("    Valid options %s" % argspec.args)
            hal_log.error("    Input options %s" % self.registration_args)
            valid = False        
        return valid        

    def is_valid(self):
        valid = True

        if self.watchpoint not in (False, 'r', 'w', 'rw', True):
            hal_log.error('Intercept: Watchpoints must be false, true, r, w, or rw on: %s' % self)
            valid = False
        
        valid &= self._check_handler_is_valid()

        if self.bp_addr is not None and type(self.bp_addr) != int:
            hal_log.error("Intercept addr invalid\n\t%s"% self)
            valid = False
        return valid

    def __repr__(self):
        if self.bp_addr is None:
            return ("(%s){symbol: %s, addr: None, class: %s, function:%s}" % \
                (self.config_file, self.symbol, self.cls, self.function))
        else:
            return ("(%s){symbol: %s, addr: %#x, class: %s, function:%s}" % \
                (self.config_file, self.symbol, self.bp_addr, self.cls, self.function))


class HalSymbolConfig(object):
    def __init__(self, config_file, name, addr, size = 0):
        self.config_file = config_file
        self.name = name
        self.addr = addr
        self.size = size

    def is_valid(self):
        return True

    def __repr__(self):
        return "SymConfig(%s){%s, %s(%i),%i}" % \
                (self.config_file, self.name, hex(self.addr), self.addr, self.size)

class HALMachineConfig:

    def __init__(self, config_file=None, arch='cortex-m3', cpu_model='cortex-m3', 
                  entry_addr=None, init_sp=None, gdb_exe='arm-none-eabi-gdb',
                  vector_base=0x08000000):
        self.arch = arch
        self.cpu_model = cpu_model
        self.entry_addr = entry_addr
        self.init_sp = init_sp
        self.gdb_exe = gdb_exe
        self.vector_base = vector_base
        self.config_file = config_file
        self._using_default_machine = True if config_file is None else False

    def __repr__(self):
        return "(%s) Machine arch:%s, cpu_type:%s, entry_addr:%#x, gdb_exe:%s" %\
        (self.arch, self.cpu_type, self.entry_addr, self.gdb_exe)


class HalucinatorConfig(object):

    def __init__(self):

        self.machine = HALMachineConfig()
        self.options = {}
        self.memories = {}
        self.intercepts = []
        self.watchpoints = []
        self.symbols = []
        self.callables = []

    def add_yaml(self, yaml_filename):
        with open(yaml_filename, 'rb') as infile:
            part_config = yaml.load(infile, Loader=yaml.FullLoader)

            if 'machine' in part_config:
                self._parse_machine(part_config['machine'], yaml_filename)
            if 'memories' in part_config:
                self._parse_memory(part_config['memories'], yaml_filename)
            if 'peripherals' in part_config:
                # Same as memories except requires emulate field
                self._parse_memory(part_config['peripherals'], yaml_filename, True)
            if 'intercepts' in part_config:
                self._parse_intercepts(part_config['intercepts'], yaml_filename)
            if 'symbols' in part_config:
                self._parse_symbols(part_config['symbols'], yaml_filename)
            if 'options' in part_config:
                self.options.update(part_config['options'])
            # Get full path for memory files in config file

    def add_csv_symbols(self, csv_file):
        '''
            Reads in a file of csv with format

            symbol_name, first_addr, last_addr
        '''
        with open(csv_file) as infile:
            reader = csv.reader(infile)
            for row in reader:
                addr = int(row[1].strip(),0)
                addr2 = int(row[2].strip(),0)
                size = addr2 - addr
                self.symbols.append(HalSymbolConfig(csv_file, row[0].strip(), addr, size))
    
    def _parse_machine(self, machine_dict, filename):
        
        prev_machine = self.machine
        self.machine = HALMachineConfig(filename, **machine_dict)
        if not prev_machine._using_default_machine:
            hal_log.warning("Overwriting previous machine %s with %s" %(prev_machine, self.machine))

    def _parse_memory(self, mem_dict, yaml_filename, emulate_required=False):
        '''
            Parsers memory config from yaml file.
        '''
        for mem_name, mem_conf in mem_dict.items():
            mem = HalMemConfig(mem_name, yaml_filename, **mem_conf)
            mem.emulate_required = emulate_required
           

            for m_name, m in self.memories.items():
                if mem_name == m.name:
                    hal_log.warning("Memory Config Overwritten:\n\tOld:%s\n\tNew:%s" % (m, mem))
                

            self.memories[mem_name] = mem

    def _parse_intercepts(self, intercept_lst, yaml_file):
        # TODO seperate the intercept handler function from, firmware reference(name/addr)
        '''
        intercepts:
            - class: halucinator.bp_handlers.SkipFunc (must be BPHandler sub class)
              addr: (firmware function_name or address) # 
              function: BSP_IO_WritePin     # Intercept function name
        '''
        for int_conf in intercept_lst:
            int_conf['cls'] = int_conf['class']
            del int_conf['class']
            intercept = HalInterceptConfig(yaml_file, **int_conf)
            self.intercepts.append(intercept)

    def _parse_symbols(self, sym_dict, yaml_file):
        for addr, sym_name in sym_dict.items():
            sym = HalSymbolConfig(yaml_file, name=sym_name, addr=addr)
            self.symbols.append(sym)

    def get_addr_for_symbol(self, sym_name):
        '''
            Gets that address for specified symbol
            
            :param sym_name:  Name of the symbol
            :ret_val None or Address: 
        '''

        for sym in self.symbols:
            if sym_name == sym.name:
                return sym.addr
        return None

    def resolve_intercept_bp_addrs(self):
        '''
            Gets all the address of all symbols in intercepts and sets the address
            appropriately.
        '''
        log.debug("Resolving Symbols")
        for inter in self.intercepts:
            if inter.bp_addr is None:
                sym_name = inter.symbol if inter.symbol is not None else inter.function
                addr = self.get_addr_for_symbol(sym_name)
                if addr is not None:
                    inter.bp_addr = addr
                    log.debug("Resolved symbol: %s, %#x" % (inter.symbol, addr))
                else:
                    log.warning("Unresolved symbol: %s, %s" % (inter.symbol, inter))

    def get_symbol_name(self, addr):
        '''
            Gets symbol name that contains address
        '''
        for sym in self.symbols:
            if addr >= sym.addr and addr <= (sym.addr + sym.size):
                return sym.name
        return None

    def memory_containing(self, addr):
        '''
            Finds the memory that contains the given address

            :param addr:  Address to find memory for
            :ret (memory, or None):
        '''
        for m_name, mem in self.memories:
            if addr >= mem.base_addr and addr < (mem.base_addr + mem.size):
                return mem
        
        return None

    def prepare_and_validate(self):
        '''
            Prepares the config for use and validates required entries are
            present. 
        '''
        self.resolve_intercept_bp_addrs()

        valid = True
        # Validate Memories
        for mem in self.memories.values():
            if not mem.is_valid():
                hal_log.error("Config: %s" % mem)
                valid = False

        # Validate Intercepts
        if len(self.intercepts) == 0:
            hal_log.warning("Intercepts is Empty")
        bp_addrs = {}
        del_inters = []
        for inter in self.intercepts:
            if not inter.is_valid():
                hal_log.error("Config: %s" % mem)
                valid = False
                if inter.bp_addr in bp_addrs:
                    hal_log.warning("Duplicate Intercept:\n\tOld: %s\n\tNew: %s" % \
                        (bp_addrs[inter.bp_addr][1], inter))
                    del_inters = bp_addrs[inter.bp_addr]
                bp_addrs[inter.bp_addr] = inter
            else:
                if self.machine.arch == 'cortex-m3' and inter.watchpoint == False and inter.bp_addr is not None:
                    inter.bp_addr &= 0xFFFFFFFE  # Clear thumb bit so BP is on right address

        for inter in del_inters:
            self.intercepts.remove(inter)

        return valid