Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains certain rights in this software.

import sqlite3
from tkinter import Tk
from tkinter.ttk import Label
import tkinter.ttk
import tkinter as tk
#from StringIO import StringIO
from io import BytesIO
import pickle
import functools
import struct

from .util.parse_symbol_tables import DWARFReader, sym_format


class lazy_property(object):
    '''
    meant to be used for lazy evaluation of an object attribute.
    property should represent non-mutable data, as it replaces itself.

    From https://stackoverflow.com/a/6849299
    '''

    def __init__(self, fget):
        self.fget = fget

        # copy the getter function's docstring and other attributes
        functools.update_wrapper(self, fget)

    def __get__(self, obj, cls):
        if obj is None:
            return self

        value = self.fget(obj)
        setattr(obj, self.fget.__name__, value)
        return value


class Recording(object):
    def __init__(self, db, row_id, funct_name, entry_id, app_id):
        self.row_id = row_id
        self.db = db
        self.funct_name = funct_name
        self.entry_id = entry_id
        self.app_id = app_id

    @lazy_property
    def before_state(self):
        '''
            Lazily set property will query DB on first access to this property
            self.before_state = {'memory':{offset: mem}, 
                                 'regs':{'<reg_name>':value}
        '''
        return self._get_state(self.entry_id)

    @lazy_property
    def after_state(self):
        '''
            Lazily set property will query DB on first access to this property
            self.after_state = {'memory':{offset: mem}, 
                                 'regs':{'<reg_name>':value}
        '''
        return self._get_state(self.row_id)

    def _get_state(self, row_id):
        '''
            Reads the state from the database and returns as a dict
        '''
        c = self.db.cursor()
        c.execute('SELECT memory, regs FROM states WHERE id == ?', (row_id,))
        memory, regs = c.fetchone()
        memory = pickle.loads(memory)
        regs = pickle.loads(regs)
        return {'memory': memory, 'regs': regs}

    def get_ret_value(self):
        #import IPython; IPython.embed()
        return self.after_state['regs']['r0']

    def get_before_value(self, addr, size):
        return self._get_value(addr, size, self.before_state)

    def get_after_value(self, addr, size):
        return self._get_value(addr, size, self.after_state)

    def _get_value(self, addr, size, state):
        for offset, mem in list(state['memory'].items()):
            print("Memory: ", hex(offset), ":", hex((offset + len(mem))))

            print("Addr: ", hex(addr))
            if addr >= offset and addr < (offset + len(mem)):
                print("Found addr in memory")
                offset_addr = addr - offset
                return mem[offset_addr:offset_addr+size]

        return ''

    def get_param(self, param_num, size=4):
        # All params need to come from before state
        if param_num < 4 and param_num >= 0:
            return self.before_state['regs']['r%i' % param_num]
        else:

            sp = self.before_state['regs']['sp']
            print("SP ", sp)
            # TODO, this is to simplistic really have to pass func definition
            # decode property.  This will work as long as non base types are
            # passed as pointers, and doubles are not used
            sp_offset = (param_num - 4) * 4
            val = struct.unpack(
                "<I", self.get_before_value(sp+sp_offset, 4))[0]
            return val


class App(object):
    def __init__(self, db_name):
        self.db = sqlite3.connect(db_name)
        self.db.text_factory = bytes
        self.root = Tk()
        self.dwarf_readers = {}
        self.create_gui_elements()
        self.root.mainloop()

    def get_dwarf_reader(self, app_id):
        if app_id not in self.dwarf_readers:
            c = self.db.cursor()
            c.execute("SELECT bin FROM applications WHERE (id == ?)", (app_id,))
            app_bin = c.fetchone()[0]
            app_bin = BytesIO(app_bin)
            self.dwarf_readers[app_id] = DWARFReader(app_bin)
        return self.dwarf_readers[app_id]

    def get_exit_records(self):
        '''
            Returns a set of function names and app_id from db 
                index 0 is function name and index 1 is app_id
        '''
        c = self.db.cursor()
        self.exit_records = {}
        for row in c.execute("SELECT id, function_name, entry_id, app_id FROM states WHERE entry_id NOT NULL"):
            self.exit_records[row[0]] = Recording(self.db, *row)
        return self.exit_records

    def create_recording_listing(self):
        '''
            Populates the tree of recordings
        '''
        records = self.get_exit_records()
        funct_lut = {}
        for r_id, rec in list(records.items()):
            f_name = rec.funct_name
            if not f_name in funct_lut:
                f_row = self.tree.insert('', tk.END, iid=f_name, text=f_name)
                funct_lut[f_name] = f_row
            # TODO change diplayed name for recording to include name of app
            self.tree.insert(funct_lut[f_name], tk.END,
                             iid=r_id, text="Exit_ID %i" % r_id)

    def create_gui_elements(self):
        '''
            Creates the elements in the GUI
        '''
        # Label for functions that are recorded
        self.table_funcs = Label(master=self.root, text="Functions")
        # self.table_funcs.config(width=400)

        # Tree of recording listings
        self.tree = tkinter.ttk.Treeview(master=self.root)
        # self.tree.column('#0', minwidth=400)
        self.tree.bind('<Button-1>', self.on_func_click)
        self.create_recording_listing()

        # Label for diplaying recording details
        self.record_label = Label(master=self.root, text="Recorded")

        # Tree for displaying record details
        self.record_tree = tkinter.ttk.Treeview(master=self.root,
                                                columns=("Type", "Name", "Size", "Before", "After"))
        self.record_tree.heading('#1', text='Type')
        self.record_tree.heading('#2', text='Name')
        self.record_tree.heading('#3', text='Size')
        self.record_tree.heading('#4', text='Entry Value')
        self.record_tree.heading('#5', text='Exit Value')
        self.record_tree.tag_configure('DIFF', background='light coral')
        self.set_layout()

    def set_layout(self):
        '''
            Sets the layout for the gui
        '''
        s = tkinter.ttk.Style()
        s.theme_use('clam')

        # Layout column 0
        self.table_funcs.grid(column=0, row=0, sticky=tk.W+tk.E)
        self.tree.grid(column=0, row=1, sticky=tk.W+tk.E+tk.N+tk.S)

        # Layout column 1
        self.record_label.grid(column=1, row=0, sticky=tk.W+tk.E)
        self.record_tree.grid(column=1, row=1, sticky=tk.W+tk.E+tk.N+tk.S)

        self.root.grid_columnconfigure(0, minsize=300)
        self.root.grid_columnconfigure(1, weight=1, minsize=500)
        self.root.grid_rowconfigure(1, weight=1)

    def display_recording(self, record):
        '''
            Displays the selected recording
        '''
        # Clear record tree
        self.record_tree.delete(*self.record_tree.get_children())

        # Get the sym_reader
        sym_reader = self.get_dwarf_reader(record.app_id)

        # Get function prototype
        funct_die = sym_reader.get_function_die(record.funct_name)
        prototype = sym_reader.get_function_prototype(record.funct_name)
        self.record_label['text'] = prototype

        # Get Return type and value
        ret_type = sym_reader.get_ret_type_str(funct_die)
        ret_value = record.get_ret_value()
        values = (ret_type, 'Return Value', None, None,
                  sym_format(ret_value, ret_type))

        ele = self.record_tree.insert('', 0, iid=funct_die.offset,
                                      values=values)
        deref = {'before': set(), 'after': set()}
        parent_values = {'before': None, 'after': ret_value}
        self.add_children(record, sym_reader, funct_die,
                          parent_values, ele, deref)

        # Add parameters to display
        for i, p_die in enumerate(sym_reader.get_parameter_dies(funct_die)):
            param_type = sym_reader.get_type_str(p_die, [])
            param_name = sym_reader.get_param_name(p_die)
            size = sym_reader.get_type_size(p_die)

            # Before and after values are same, returned by reference
            p_value = record.get_param(i)
            f_value = sym_format(p_value, param_type)

            values = (param_type, param_name, size, f_value, f_value)
            row = self.record_tree.insert(
                '', tk.END, iid=p_die.offset, values=values)
            parent_values = {'before': p_value, 'after': p_value}
            deref = {'before': set(), 'after': set()}
            self.add_children(record, sym_reader, p_die,
                              parent_values, row, deref)

    def add_children(self, record, sym_reader, sym_die, parent_values, parent,
                     deref_addrs):
        '''
            Adds symbol to the record tree
        '''

        if 'DW_AT_type' in sym_die.attributes:
            type_die = sym_reader.get_referenced_die('DW_AT_type', sym_die)
            if type_die.tag == 'DW_TAG_pointer_type':
                # Add children which is derefence of this value
                ty_str = sym_reader.get_type_str(type_die)
                pts2type = sym_reader.get_referenced_die(
                    'DW_AT_type', type_die)
                if pts2type == None:
                    ty_size = 4
                else:
                    ty_size = sym_reader.get_type_size(pts2type)
                b_ptr = parent_values['before']
                a_ptr = parent_values['after']

                if not b_ptr in deref_addrs['before'] or \
                   not a_ptr in deref_addrs['after']:

                    # If before value is a str of bytes convert to int
                    if type(b_ptr) == str and len(b_ptr) == 4:
                        b_ptr = struct.unpack('<I', b_ptr)[0]
                    if type(a_ptr) == str and len(a_ptr) == 4:
                        a_ptr = struct.unpack('<I', a_ptr)[0]

                    # If ptr is an int, dereference it
                    if type(b_ptr) == int:
                        before_val = record.get_before_value(b_ptr, ty_size)
                        deref_addrs['before'].add(b_ptr)
                    else:
                        before_val = ''
                    if type(a_ptr) == int:
                        after_val = record.get_after_value(a_ptr, ty_size)
                        deref_addrs['after'].add(a_ptr)
                    else:
                        after_val = ''

                    values = (ty_str, '', ty_size, sym_format(before_val, ty_str),
                              sym_format(after_val, ty_str))
                    row = self.record_tree.insert(
                        parent, tk.END, values=values)
                    self.tag_if_diff(row, before_val, after_val)

                    parent_values['before'] = before_val
                    parent_values['after'] = after_val
                    self.add_children(record, sym_reader, type_die,
                                      parent_values, row, deref_addrs)
                else:
                    values = (ty_str, '', ty_size, "Already Derefed",
                              "Already Derefed")
                    row = self.record_tree.insert(
                        parent, tk.END, values=values)

            elif type_die.tag == 'DW_TAG_const_type':
                self.add_children(record, sym_reader, type_die,
                                  parent_values, parent, deref_addrs)
                pass
            elif type_die.tag == 'DW_TAG_volatile_type':
                self.add_children(record, sym_reader, type_die,
                                  parent_values, parent, deref_addrs)
            elif type_die.tag == 'DW_TAG_union_type':
                pass
            elif type_die.tag == 'DW_TAG_array_type':
                pass
            elif type_die.tag == 'DW_TAG_typedef':
                self.add_children(record, sym_reader, type_die,
                                  parent_values, parent, deref_addrs)
            elif type_die.tag == 'DW_TAG_enumeration_type':
                # TODO make enum string cover span all columns

                row = self.add_record_row(parent, sym_reader, type_die,
                                          None, None, None)
            elif type_die.tag == 'DW_TAG_subroutine_type':
                # Happens with funciton ptrs
                # raise NotImplementedError("Didn't expect Subroutine type")
                pass
            elif type_die.tag == 'DW_TAG_structure_type':
                offset = 0
                for child in type_die.iter_children():
                    child_name = child.attributes['DW_AT_name'].value
                    c_size = sym_reader.get_type_size(child)
                    b_val = parent_values['before'][offset:offset+c_size]
                    a_val = parent_values['after'][offset:offset+c_size]
                    offset += c_size

                    row = self.add_record_row(parent, sym_reader, child,
                                              child_name, b_val, a_val)
                    parent_vals = {'before': b_val, 'after': a_val}
                    self.add_children(record, sym_reader, child,
                                      parent_vals, row, deref_addrs)

                print("Structure")
            elif type_die.tag == 'DW_TAG_base_type':
                pass
            else:
                print(type_die.tag)
                # These are likely primitives don't need to add children
                pass

    def tag_if_diff(self, row, a_val, b_val):
        if b_val != a_val:
            r_id = row
            while r_id != '':
                self.record_tree.item(r_id, tag='DIFF')
                r_id = self.record_tree.parent(r_id)

    def add_record_row(self, parent, sym_reader, sym_die, name, b_val, a_val):
        if sym_die.tag == 'DW_TAG_enumeration_type':
            ty = sym_reader.get_enum_str(sym_die)
        else:
            ty = sym_reader.get_type_str(sym_die)

        ty_size = sym_reader.get_type_size(sym_die)
        val = (ty, name, ty_size, sym_format(b_val, ty), sym_format(a_val, ty))
        row = self.record_tree.insert(parent, tk.END, values=val)
        self.tag_if_diff(row, a_val, b_val)
        return row

    def on_func_click(self, event):
        clicked_id = self.tree.identify('item', event.x, event.y)
        try:
            iid = int(clicked_id)
            if iid in self.exit_records:
                print("Displaying Record")
                self.display_recording(self.exit_records[iid])
        except ValueError:
            pass


if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('-d', '--database', required=True,
                   help='Recorded Database')

    args = p.parse_args()
    App(args.database)
