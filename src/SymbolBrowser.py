# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. 
# Government retains certain rights in this software.

import sqlite3
from tkinter import Tk, ttk, Label
import tkinter as tk
from tools.parse_symbol_tables import DWARFReader, sym_format
#from StringIO import StringIO
from io import BytesIO
import pickle
import functools
import struct


class App(object):
    def __init__(self, elf_filename):
        self.root = Tk()
        with open(elf_filename, 'rb') as elf_file:
            self.dwarf_reader = DWARFReader(elf_file)
        self.create_gui_elements()
        self.root.mainloop()

        
    def create_recording_listing(self):
        '''
            Populates the functions tree
        '''
        for f_name in sorted(self.dwarf_reader.function_lut.keys()):
            f_row = self.tree.insert('', tk.END, iid=f_name, text=f_name)
                
            #TODO change diplayed name for recording to include name of app
            # self.tree.insert(funct_lut[f_name], tk.END, iid=r_id, text="Exit_ID %i" % r_id)

    def create_gui_elements(self):
        '''
            Creates the elements in the GUI
        '''
        # Label for functions that are recorded
        self.table_funcs = Label(master=self.root, text= "Functions")       
        #self.table_funcs.config(width=400)
        
        # Tree of recording listings
        self.tree = ttk.Treeview(master=self.root)
        #self.tree.column('#0', minwidth=400)
        self.tree.bind('<Button-1>', self.on_func_click)
        self.create_recording_listing()
        
        # Label for diplaying recording details
        self.record_label = Label(master=self.root, text="Recorded")      

        # Tree for displaying record details
        self.record_tree = ttk.Treeview(master=self.root, 
                             columns=("Type","Name","Size", "Before", "After"))
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
        s = ttk.Style()
        s.theme_use('clam')

        #Layout column 0
        self.table_funcs.grid(column=0, row=0, sticky=tk.W+tk.E)
        self.tree.grid(column=0, row=1, sticky=tk.W+tk.E+tk.N+tk.S)

        #Layout column 1
        self.record_label.grid(column=1, row=0,sticky=tk.W+tk.E)
        self.record_tree.grid(column=1, row=1, sticky=tk.W+tk.E+tk.N+tk.S)
        
        self.root.grid_columnconfigure(0, minsize=300)
        self.root.grid_columnconfigure(1, weight=1, minsize=500)
        self.root.grid_rowconfigure(1, weight=1)
  
    def display_recording(self, funct_name):
        '''
            Displays the selected function
        '''
        # Clear record tree
        self.record_tree.delete(*self.record_tree.get_children())
        
        # Get the sym_reader
        sym_reader = self.dwarf_reader
        
        # Get function prototype
        funct_die = sym_reader.get_function_die(funct_name)
        prototype = sym_reader.get_function_prototype(funct_name)
        self.record_label['text'] = prototype

        #Get Return type and value
        ret_type = sym_reader.get_ret_type_str(funct_die)
        ret_value = None
        values = (ret_type, 'Return Value', None, None, sym_format(ret_value, ret_type))

        ele = self.record_tree.insert('', 0, iid=funct_die.offset, 
                              values=values)
        deref = {'before':set(), 'after':set()}
        parent_values = {'before': None, 'after': ret_value}
        self.add_children(funct_name, sym_reader, funct_die, parent_values, ele, deref)

        # Add parameters to display
        for i, p_die in enumerate(sym_reader.get_parameter_dies(funct_die)):
            param_type = sym_reader.get_type_str(p_die,[])
            param_name = sym_reader.get_param_name(p_die)
            size = sym_reader.get_type_size(p_die)
            
            # Before and after values are same, returned by reference
            p_value = None # record.get_param(i)
            f_value = sym_format(p_value, param_type)
            
            values =  (param_type, param_name, size, f_value, f_value)
            row = self.record_tree.insert('', tk.END, iid=p_die.offset, values=values)
            parent_values = {'before': p_value, 'after': p_value}
            deref = {'before':set(), 'after':set()}
            self.add_children(funct_name, sym_reader, p_die, parent_values, row, deref)
    
    def add_children(self, funct_name, sym_reader, sym_die, parent_values, parent,
                     deref_addrs):
        '''
            Adds symbol to the record tree
        '''
        
        if 'DW_AT_type' in sym_die.attributes:       
            type_die = sym_reader.get_referenced_die('DW_AT_type', sym_die)
            if type_die.tag == 'DW_TAG_pointer_type':
                # Add children which is derefence of this value
                ty_str = sym_reader.get_type_str(type_die)
                pts2type= sym_reader.get_referenced_die('DW_AT_type', type_die)
                if pts2type == None:
                    ty_size = 4
                else:
                    ty_size = sym_reader.get_type_size(pts2type)
                b_ptr = parent_values['before']
                a_ptr = parent_values['after']

                if not b_ptr in deref_addrs['before'] or \
                   not a_ptr in deref_addrs['after']:
                    
                    # If before value is a str of bytes convert to int
                    if type(b_ptr) == str and len(b_ptr) == 4 :
                        b_ptr = struct.unpack('<I',b_ptr)[0]
                    if type(a_ptr) == str and len(a_ptr) == 4:
                        a_ptr = struct.unpack('<I',a_ptr)[0]
                    
                    # If ptr is an int, dereference it
                    if type(b_ptr) == int:
                        before_val = None #record.get_before_value(b_ptr, ty_size)
                        deref_addrs['before'].add(b_ptr)
                    else:
                        before_val = ''
                    if type(a_ptr) == int:
                        after_val = None #record.get_after_value(a_ptr, ty_size)
                        deref_addrs['after'].add(a_ptr)
                    else:
                        after_val = ''

                    values = (ty_str, '', ty_size, sym_format(before_val,ty_str),
                            sym_format(after_val, ty_str))
                    row = self.record_tree.insert(parent,tk.END,values=values)
                    self.tag_if_diff(row, before_val, after_val)

                    parent_values['before'] = before_val
                    parent_values['after'] = after_val
                    self.add_children(funct_name, sym_reader, type_die, 
                                      parent_values, row, deref_addrs)
                else:
                    values = (ty_str, '', ty_size, "Already Derefed",
                              "Already Derefed")
                    row = self.record_tree.insert(parent,tk.END,values=values)
                
            elif type_die.tag == 'DW_TAG_const_type':
                self.add_children(funct_name, sym_reader, type_die, 
                                  parent_values, parent, deref_addrs)
                pass
            elif type_die.tag == 'DW_TAG_volatile_type':
                self.add_children(funct_name, sym_reader, type_die, 
                                  parent_values, parent, deref_addrs)
            elif type_die.tag == 'DW_TAG_union_type':
                pass
            elif type_die.tag == 'DW_TAG_array_type':
                pass
            elif type_die.tag == 'DW_TAG_typedef':
                self.add_children(funct_name, sym_reader, type_die, 
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
                    parent_vals = {'before': b_val, 'after':a_val}
                    self.add_children(funct_name, sym_reader, child, 
                                      parent_vals, row, deref_addrs)
                    
                print "Structure"
            elif type_die.tag == 'DW_TAG_base_type':
                pass
            else:
                print type_die.tag
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
        clicked_id =  self.tree.identify('item',event.x,event.y)
        try:
            #iid = int(clicked_id)
            #if iid in self.exit_records:
            #print clicked_id
            self.display_recording(clicked_id)
        except ValueError:
            pass


if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('-e', '--elf', required=True, 
                   help='elf file')

    args = p.parse_args()
    App(args.elf)
