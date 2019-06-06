# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC 
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a 
# non-exclusive license for use of this work by or on behalf of the U.S. 
# Government. Export of this data may require a license from the United States 
# Government.

import yaml
from avatar2 import Avatar, GDBTarget, ARM_CORTEX_M3, TargetStates
import logging
import os
from IPython import embed
import sqlite3
import hashlib
import pickle
from collections import deque, defaultdict


class State_Recorder(object):

    def __init__(self, db_name, gdb, memories, elf_file):

        self.db_name = db_name
 
        self.memories = memories
        self.gdb = gdb
        self.break_points = {}
        self.call_stack = deque()
        self.ret_addrs = defaultdict(deque)

        db = sqlite3.connect(self.db_name)
        db.text_factory = bytes
        self.create_sql_tables(db)
        self.get_app_id(elf_file, db)
        db.close()


    def add_function(self, function):
        # * on break point sets on first instruction, not first line of code from source
        bp = self.gdb.set_breakpoint("*"+function)
        self.break_points[bp] = (function, True)


    def set_exit_bp(self, function, entry_id):
        
        ret_addr = self.gdb.regs.lr
        ret_addr &= 0xFFFFFFFE  # Clearing Thumb bit, causes jTrace debugger issues
        if len(self.ret_addrs['ret_addr']) == 0:
            print "Adding Breakpoint on addr: ", ret_addr, " for Function ", function
            self.ret_addrs[ret_addr].append((function, entry_id))
            bp = self.gdb.set_breakpoint(ret_addr) 
            self.break_points[bp] = (function, False)
        else:
            self.ret_addrs[ret_addr].append((function, entry_id))


    def create_sql_tables(self, db):
        '''
            Creates the SQL database for recording data into
            args:
                conn(sqlite2.connection):  Sqlite3 connection assumes already connected
        '''
       
        cursor = db.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS applications (id INTEGER PRIMARY KEY, name TEXT, sha1 TEXT, bin BLOB)")
        cursor.execute('''CREATE TABLE IF NOT EXISTS states (id INTEGER PRIMARY KEY,
                            app_id INTEGER, 
                            function_name TEXT,
                            entry_id INTEGER,  memory BLOB, regs BLOB)''')
        # NOTE: Entry state records will have NULL entry_id's, Exits will reference
        # the id of the entry state record
        db.commit()


    def get_app_id(self, elf_file, db):
        self.elf_file = elf_file
        with open(elf_file, 'rb') as elf_fd:
            elf_bin = elf_fd.read()
        
        c = db.cursor()
        sha1 = hashlib.sha1(elf_bin)
        sha1_digest = sha1.hexdigest()
        print sha1_digest, type(sha1_digest)
        c.execute("SELECT id FROM applications WHERE sha1==(?)", (sha1_digest,))
        row = c.fetchone()
        print "Row: ", row
        if row == None:
            c.execute("INSERT INTO applications(name, sha1, bin) VALUES(?,?,?)", 
                (elf_file, sha1_digest, elf_bin))
            db.commit()
            self.app_id = c.lastrowid
        else:
            self.app_id = row[0]


    def save_state_to_db(self, function, is_entry):
        '''
            Saves the processor's state to the database
            args:
                bp_id(int): Break point id to look up entry_id, function
        ''' 
        db = sqlite3.connect(self.db_name)       
        memories, regs = self.get_state()
        mem = pickle.dumps(memories)
        regs = pickle.dumps(regs)
        c = db.cursor()
        if is_entry:
            c.execute('''INSERT INTO states (app_id, function_name, 
                         memory, regs) VALUES(?,?,?,?)''',(self.app_id, 
                         function,mem, regs))
        else:
            func, entry_id = self.call_stack.pop()
            if func != function:
                # TODO   Handle Tail calls
                error_str = "Call stack is off: %s != %s" % (func, function)
                raise ValueError(error_str)

            c.execute('''INSERT INTO states (app_id, function_name, 
                         memory, regs, entry_id) VALUES (?,?,?,?,?)''', (self.app_id, 
                         function, mem, regs, entry_id))
        db.commit()
        record_id = c.lastrowid
        db.close()
        if is_entry:
            self.call_stack.append((function, record_id))
        return record_id


    def get_state(self):
        '''
            Gets the processor state
        '''
        mems = {}
        for (start, size) in self.memories:
            mems[start] = self.gdb.read_memory(start, 1, size, raw=True)

        registers = {}
        for reg in self.gdb.avatar.arch.registers:
            registers[reg] = self.gdb.read_register(reg)
        return mems, registers


    def handle_bp(self, bp):
        (function, is_entry) = self.break_points[bp]
        print "BP Hit: ", function, " is_enrty: ", is_entry
        record_id = self.save_state_to_db(function, is_entry)
        if is_entry: 
            # This is an entry set bp for exit
            self.set_exit_bp(function, record_id) 
        else:
            # This is an exit remove break point if no longer needed
            pc = self.gdb.regs.pc & 0xFFFFFFE # Clear Thumb bit
            self.ret_addrs[pc].pop()
            if len(self.ret_addrs[pc]) == 0:
                del(self.break_points[bp])
                self.gdb.remove_breakpoint(bp)


def handle_bp(avatar, message):
    global Recorder 
    bp = int(message.breakpoint_number)
    Recorder.handle_bp(bp)
    message.origin.cont()


# Command to start jTrace
# /opt/SEGGER/JLink/JLinkGDBServer -endian little -localhostonly -device STM32F479NI -if SWD

if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument("-e",'--elf', required=True,
                   help='Elf file to profile')
    p.add_argument("-f",'--functions', required=True,
                   help='YAML file listing functions')
    p.add_argument("-d",'--db',
                   help='sqlite3 database filename')
    args = p.parse_args()

    avatar = Avatar(arch=ARM_CORTEX_M3, output_directory='/tmp/hal_profile')
    gdb = avatar.add_target(GDBTarget, gdb_additional_args=[args.elf],
                             gdb_executable="arm-none-eabi-gdb", gdb_port=2331)


    avatar.watchmen.add_watchman('BreakpointHit', 'before', 
                                 handle_bp, is_async=True)
    avatar.init_targets()

    
    memories = [(0x20000000, 0x50000)]
    if args.db == None:
        db = os.path.splitext(args.elf)[0] + ".sqlite"
    else:
        db = args.db

    Recorder = State_Recorder(db, gdb, memories, args.elf)
    
    with open(args.functions,'rb') as infile:
       functions = yaml.safe_load(infile)

    for f in functions:
        print "Setting Breakpoint: ", f
        Recorder.add_function(f)
    gdb.protocols.execution.console_command('load')
    gdb.protocols.execution.console_command('monitor reset')
    gdb.cont()
    embed()
    gdb.stop()
    avatar.shutdown()
