Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains certain rights in this software.


import argparse
import os
import sys
import string
import IPython
from elftools.common.exceptions import ELFError
from elftools.elf.elffile import ELFFile
from elftools.elf.constants import E_FLAGS
import binascii
import struct

# Little endian format strings
LE_FORMAT_STRS = {'uint32_t': '<I', "uint16_t": '<H', 'uint8_t': '<B',
                  'int32_t': '<i', "uint16_t": '<h', 'uint8_t': '<b'}

# Big endian format strings
BE_FORMAT_STRS = {'uint32_t': '>I', "uint16_t": '>H', 'uint8_t': '>B',
                  'int32_t': '>i', "uint16_t": '>h', 'uint8_t': '>b'}


def sym_format(value, ty_str, is_le=True):
    '''
        Formats the value using the die to determine how convert to a string
        Args:
            value:  The value to be converted
            die: DWARF symbol from elftools
            is_le:  Is little endian
    '''

    if value == None or value == '':
        return value
    elif type(value) == int:
        return hex(value)
    else:
        try:
            if is_le:
                if ty_str in LE_FORMAT_STRS:
                    return hex(struct.unpack(LE_FORMAT_STRS[ty_str], value)[0])
                elif '*' in ty_str:
                    return hex(struct.unpack("<I", value)[0])
            else:
                if ty_str in BE_FORMAT_STRS:
                    return hex(struct.unpack(LE_FORMAT_STRS[ty_str], value)[0])
                elif '*' in ty_str:
                    return hex(struct.unpack(">I", value)[0])
        except struct.error:
            return "Parse_Err: %s" % binascii.hexlify(value)

        if len(value) <= 16:
            return binascii.hexlify(value[0:16])
        else:
            return binascii.hexlify(value[0:16]) + "..."


class DWARFReader(object):
    # Useful DWARF Info http://dwarfstd.org/doc/Debugging%20using%20DWARF-2012.pdf
    def __init__(self, filename):
        self._elffile = ELFFile(filename)
        self._dwarf = self._elffile.get_dwarf_info()
        self._build_offset_lut()

    def _build_offset_lut(self):
        '''
            Builds a LUTs for for DIE objects using the offset
        '''
        self.offset_lut = {}
        self.function_lut = {}
        self.typedef_lut = {}
        for cu in self._dwarf.iter_CUs():
            for die in cu.iter_DIEs():
                if die.offset in self.offset_lut:
                    raise ValueError("Collision on Symbols Offsets")
                self.offset_lut[die.offset] = die
                if die.tag == 'DW_TAG_subprogram':
                    if 'DW_AT_name' in die.attributes:
                        self.function_lut[die.attributes['DW_AT_name'].value] = die

                elif die.tag == 'DW_TAG_typedef':
                    if 'DW_AT_name' in die.attributes:
                        self.typedef_lut[die.attributes['DW_AT_name'].value] = die

    def get_referenced_die(self, attr_str, die):
        try:
            attr = die.attributes[attr_str]
            offset = attr.value + die.cu.cu_offset
            return self.offset_lut[offset]
        except KeyError:
            return None

    def get_type_size(self, die):
        if 'DW_AT_byte_size' in die.attributes:
            return die.attributes['DW_AT_byte_size'].value
        elif 'DW_AT_type' in die.attributes:
            type_die = self.get_referenced_die('DW_AT_type', die)
            return self.get_type_size(type_die)
        else:
            return -1

    def get_type_str(self, die, str_list=None):
        '''
            Returns a C type declaration for the type of the die passed in
        '''
        if str_list == None:
            str_list = []
        if 'DW_AT_type' in die.attributes:
            type_die = self.get_referenced_die('DW_AT_type', die)
            if type_die.tag == 'DW_TAG_pointer_type':
                self.get_type_str(type_die, str_list)
                str_list.append('*')
            elif type_die.tag == 'DW_TAG_const_type':
                str_list.append("const")
                self.get_type_str(type_die, str_list)
            elif type_die.tag == 'DW_TAG_volatile_type':
                str_list.append("volatile")
                self.get_type_str(type_die, str_list)
            elif type_die.tag == 'DW_TAG_union_type':
                members = []
                for c in type_die.iter_children():
                    member_str = self.get_type_str(c, [])
                    members.append(member_str)
                if len(members) == 1:
                    str_list.append("union {%s};" % (member_str[0]))
                else:
                    str_list.append("union {%s};" % (",".join(member_str)))
            elif type_die.tag == 'DW_TAG_array_type':
                self.get_type_str(type_die, str_list)
                str_list.append("[]")
            elif type_die.tag == 'DW_TAG_enumeration_type':
                str_list.append("enum")
                self.get_type_str(type_die, str_list)
            elif type_die.tag == 'DW_TAG_subroutine_type':
                params = []
                for c in type_die.iter_children():
                    param_str = self.get_type_str(c, [])
                    params.append(param_str)
                if len(params) == 1:
                    str_list.append("(%s)" % (params[0]))
                else:
                    str_list.append("(%s)" % (",".join(params)))
            else:
                type_name = type_die.attributes['DW_AT_name'].value
                str_list.append(type_name)
        else:
            str_list.append("void")
        return " ".join(str_list)
        # except Exception as e:
        #     print e
        #     print type_die
        #     IPython.embed()

    def get_parameter_dies(self, funct_die):
        params = []
        for child in funct_die.iter_children():
            if child.tag == 'DW_TAG_formal_parameter':
                params.append(child)
        return params

    def get_ret_type_str(self, funct_die):
        if 'DW_AT_type' in funct_die.attributes:
            ret_type = self.get_type_str(funct_die)
        else:
            ret_type = 'void'
        return ret_type

    def get_function_parameters(self, funct_die):
        '''
            Returns a C type declaration for the function infor passed in

            args: 
                funct_die:  A Die for a function
        '''
        if funct_die.tag != 'DW_TAG_subprogram':
            raise TypeError('funct_die.tag not a of type DW_TAG_subprogram')

        name = funct_die.attributes['DW_AT_name'].value
        params = []
        for child in funct_die.iter_children():
            if child.tag == 'DW_TAG_formal_parameter':
                param_type_str = self.get_type_str(child)
                param_name = child.attributes['DW_AT_name'].value
                params.append(param_type_str + " " + param_name)
        ret_type = self.get_ret_type_str(funct_die)
        return "%s %s(%s);" % (ret_type, name, ", ".join(params))

    def get_function_die(self, f_name):
        return self.function_lut[f_name]

    def get_return_type_die(self, func_die):
        return

    def get_function_prototype(self, f_name):
        f_die = self.function_lut[f_name]
        return self.get_function_parameters(f_die)

    def get_param_name(self, param_die):
        return param_die.attributes['DW_AT_name'].value

    def get_typedef_desc_from_str(self, typedef_str):
        '''
            Prints definition of the typedef name
        '''
        tydef_die = self.typedef_lut[typedef_str]
        return self.get_typedef_desc_from_die(tydef_die)

    def get_enum_str(self, enum_die):
        member_strs = []
        for child in enum_die.iter_children():
            if child.tag == 'DW_TAG_enumerator':
                child_name = child.attributes['DW_AT_name'].value
                value = child.attributes['DW_AT_const_value'].value
                member_strs.append("%s=%s;" % (child_name, hex(value)))
        return "enum {%s}; " % (" ".join(member_strs))

    def get_typedef_desc_from_die(self, tydef_die):
        # print '='*80
        # print typedef_str
        # print tydef_die
        name = tydef_die.attributes['DW_AT_name'].value
        type_die = self.get_referenced_die('DW_AT_type', tydef_die)
        # print "TYPE_DIE", type_die
        if 'DW_AT_byte_size' in type_die.attributes:
            size = type_die.attributes['DW_AT_byte_size'].value
        else:
            size = None
        member_strs = []
        if type_die.tag == 'DW_TAG_structure_type':

            for child in type_die.iter_children():
                child_name = child.attributes['DW_AT_name'].value
                child_type_str = self.get_type_str(child)
                c_size = self.get_type_size(child)
                decl_str = '\t%s %s; Size: %i\n' % (
                    child_type_str, child_name, c_size)

                member_strs.append(decl_str)
            ret_str = "struct %s {\n%s};" % (name, "".join(member_strs))
        elif type_die.tag == 'DW_TAG_enumeration_type':
            ret_str = self.get_enum_str(type_die)
        elif type_die.tag == 'DW_TAG_pointer_type':
            size = self.get_type_size(type_die)
            ret_str = (self.get_type_str(type_die) + " * ; Size: " + str(size))
        # if type_die.tag == 'DW_TAG_base_type':
        else:
            size = self.get_type_size(type_die)
            ret_str = (self.get_type_str(type_die) + "Size: " + str(size))
        # else:
        #    print "Unhandled type"
        #    print type_die
        return ret_str, size


def main(stream=None):
    # parse the command-line arguments and invoke ReadElf
    argparser = argparse.ArgumentParser(
        usage='usage: %(prog)s [options] <elf-file>',
        description="Parses DWARF debugging from elf file",
        prog='readelf.py')
    argparser.add_argument('file',
                           nargs='?', default=None,
                           help='ELF file to parse',)

    args = argparser.parse_args()

    if not args.file:
        argparser.print_help()
        sys.exit(0)

    with open(args.file, 'rb') as file:
        try:
            print("Running")
            reader = DWARFReader(file)
            print(reader.get_function_prototype('ETH_DMAReceptionEnable'))
            decl, size = reader.get_typedef_desc_from_die(
                'ETH_DMARxFrameInfos')
            print(decl, "Size: ", size)
        except ELFError as ex:
            sys.stderr.write('ELF error: %s\n' % ex)
            sys.exit(1)


# -------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
    # profile_main()
