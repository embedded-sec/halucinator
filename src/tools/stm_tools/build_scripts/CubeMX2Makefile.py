#!/usr/bin/env python
#  File was modified to automatically fix case of files
# Modified from https://github.com/baoshi/CubeMX2Makefile

import sys
import re
import shutil
import os
import os.path
import string
import xml.etree.ElementTree
import json


BUILD_INFO_FILE = 'build_info.json'

# Return codes
C2M_ERR_SUCCESS = 0
C2M_ERR_INVALID_COMMANDLINE = -1
C2M_ERR_LOAD_TEMPLATE = -2
C2M_ERR_NO_PROJECT = -3
C2M_ERR_PROJECT_FILE = -4
C2M_ERR_IO = -5
C2M_ERR_NEED_UPDATE = -6

GCC_PATH = None
LLVM_PATH = None

mcu_regex_to_cflags_dict = None
mcu_regex_to_float_abi_dict = None
mcu_regex_to_libs_dict = None
mcu_regex_to_syscalls_dict = None
mcu_regex_to_comp_support_dict = None


def build_LUTS():
    global mcu_regex_to_cflags_dict
    global mcu_regex_to_float_abi_dict
    global mcu_regex_to_libs_dict
    global mcu_regex_to_syscalls_dict
    global mcu_regex_to_comp_support_dict

    # STM32 MCU to compiler flags.
    # modified Cortex M4,7 devices get compiled as M3 for QEMU
    mcu_regex_to_cflags_dict = {
        'STM32(F|L)0': '-mcpu=cortex-m0',
        'STM32(F|L)1': '-mcpu=cortex-m3',
        'STM32(F|L)2': '-mcpu=cortex-m3',
        #    'STM32(F|L)3': '-mthumb -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard',
        'STM32(F|L)3': '-mcpu=cortex-m3',
        #    'STM32(F|L)4': '-mthumb -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard',
        'STM32(F|L)4': '-mcpu=cortex-m3',
        'STM32(F|L)7': '-mcpu=cortex-m3',  # -mfloat-abi=hard',
    }

    mcu_regex_to_float_abi_dict = {
        'STM32(F|L)0': 'soft',
        'STM32(F|L)1': 'soft',
        'STM32(F|L)2': 'soft',
        #    'STM32(F|L)3': '-mthumb -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard',
        'STM32(F|L)3': 'soft',
        #    'STM32(F|L)4': '-mthumb -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard',
        'STM32(F|L)4': 'soft',
        'STM32(F|L)7': 'soft',  # -mfloat-abi=hard',
    }

    mcu_regex_to_libs_dict = {
        'STM32(F|L)0': '-L %s/arm-none-eabi/lib/thumb/v6-m -L %s/lib/gcc/arm-none-eabi/6.3.1/thumb/v6-m' % (GCC_PATH, GCC_PATH),
        'STM32(F|L)1': '-L %s/arm-none-eabi/lib/thumb/v7-m -L %s/lib/gcc/arm-none-eabi/6.3.1/thumb/v7-m' % (GCC_PATH, GCC_PATH),
        'STM32(F|L)2': '-L %s/arm-none-eabi/lib/thumb/v7-m -L %s/lib/gcc/arm-none-eabi/6.3.1/thumb/v7-m' % (GCC_PATH, GCC_PATH),
        #    'STM32(F|L)3': '-mthumb -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard',
        'STM32(F|L)3': '-L %s/arm-none-eabi/lib/thumb/v7e-m -L %s/lib/gcc/arm-none-eabi/6.3.1/thumb/v7e-m' % (GCC_PATH, GCC_PATH),
        #    'STM32(F|L)4': '-mthumb -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard',
        'STM32(F|L)4': '-L %s/arm-none-eabi/lib/thumb/v7e-m -L %s/lib/gcc/arm-none-eabi/6.3.1/thumb/v7e-m' % (GCC_PATH, GCC_PATH),
        # -mfloat-abi=hard',
        'STM32(F|L)7': '-L %s/arm-none-eabi/lib/thumb/v7e-m -L %s/lib/gcc/arm-none-eabi/6.3.1/thumb/v7e-m' % (GCC_PATH, GCC_PATH),
    }

    mcu_regex_to_syscalls_dict = {
        'STM32(F|L)0': 'syscalls-v6-m.o',
        'STM32(F|L)1': 'syscalls-v7-m.o',
        'STM32(F|L)2': 'syscalls-v7-m.o',
        #    'STM32(F|L)3': thumb -mcpu=corte4-sp-d16 -mfloat-abi=hard',
        'STM32(F|L)3': 'syscalls-v7e-m.o',
        #    'STM32(F|L)4': thumb -mcpu=corte-sp-d16 -mfloat-abi=hard',
        'STM32(F|L)4': 'syscalls-v7e-m.o',
        'STM32(F|L)7': 'syscalls-v7e-m.o',  # -mfloat-abi=hard',
    }


def fixup_lib_names(lib):
    '''
        This library names are in the form of :lib*.a, Need to just get the *
        Also currently only supporting Soft float so need to change CM4F to CM4
    '''
    # print lib
    name = os.path.splitext(lib)[0]  # remove extention
    name = name[4:]  # remove the :lib
    if 'CM4F' in name:
        name = name.replace('CM4F', 'CM4')
    # print name
    return name


def fix_path_caps(filename, path):
    '''
        Needed because projects were created on windows which uses case
        insensitive paths
        Here we try to find a path that has correct capitalization
    '''
    cur_path = path
    full_path = os.path.join(path, filename)
    if os.path.exists(full_path):
        return filename

    valid_path = []
    for next_element in filename.split(os.path.sep):
        temp_path = os.path.join(cur_path, next_element)
        if os.path.exists(temp_path):
            valid_path.append(next_element)
            cur_path = temp_path
        else:
            found = False
            for element in os.listdir(cur_path):
                if element.lower() == next_element.lower():
                    cur_path = os.path.join(cur_path, element)
                    valid_path.append(element)

                    found = True
                    break
            if not found:
                return None  # Can't find matching directory
    fixed_path = os.path.sep.join(valid_path)
    print("Changed Dir Name")
    print("From: ", filename)
    print("To:   ", fixed_path)
    return fixed_path


def get_project_name():
    if os.path.exists(BUILD_INFO_FILE):
        with open(BUILD_INFO_FILE, 'rb') as info_file:
            info = json.load(info_file)
    else:
        info = {}
        info['BOARD'] = input("Board: ")
        info['APP'] = input("APP: ")
        with open(BUILD_INFO_FILE, 'wb') as info_file:
            json.dump(info, info_file)

    project_name = info['APP'] + '--board=' + info['BOARD']
    return project_name


def main():
    global GCC_PATH
    global LLVM_PATH

    if len(sys.argv) != 2:
        sys.stderr.write("\nSTM32CubeMX project to Makefile V1.9\n")
        sys.stderr.write("-==================================-\n")
        sys.stderr.write(
            "Initially written by Baoshi <mail\x40ba0sh1.com> on 2015-02-22\n")
        sys.stderr.write(
            "Updated 2016-06-14 for STM32CubeMX 4.15.1 http://www.st.com/stm32cube\n")
        sys.stderr.write("Refer to history.txt for contributors, thanks!\n")
        sys.stderr.write(
            "Apache License 2.0 <http://www.apache.org/licenses/LICENSE-2.0>\n")
        sys.stderr.write("\nUsage:\n")
        sys.stderr.write("  CubeMX2Makefile.py <SW4STM32 project folder>\n")
        sys.exit(C2M_ERR_INVALID_COMMANDLINE)

    # Load template files
    app_folder_path = os.path.dirname(os.path.abspath(sys.argv[0]))

    template_file_path = os.path.join(app_folder_path, 'CubeMX2Makefile.tpl')
    try:
        with open(template_file_path, 'rb') as f:
            makefile_template = string.Template(f.read())
    except EnvironmentError as e:
        sys.stderr.write("Unable to read template file: {}. Error: {}".format(
            template_file_path, str(e)))
        sys.exit(C2M_ERR_LOAD_TEMPLATE)

    proj_folder_path = os.path.abspath(sys.argv[1])
    if not os.path.isdir(proj_folder_path):
        sys.stderr.write(
            "STM32CubeMX \"Toolchain Folder Location\" not found: {}\n".format(proj_folder_path))
        sys.exit(C2M_ERR_INVALID_COMMANDLINE)

    #proj_name = os.path.splitext(os.path.basename(proj_folder_path))[0]
    proj_name = get_project_name()
    ac6_project_path = os.path.join(proj_folder_path, '.project')
    ac6_cproject_path = os.path.join(proj_folder_path, '.cproject')
    if not (os.path.isfile(ac6_project_path) and os.path.isfile(ac6_cproject_path)):
        sys.stderr.write(
            "SW4STM32 project not found, use STM32CubeMX to generate a SW4STM32 project first\n")
        sys.exit(C2M_ERR_NO_PROJECT)

    # Configuration
    GCC_PATH = 'arm-none-eabi-g++'

    build_LUTS()

    ctx = []

    c_set = {}
    c_set['source_endswith'] = '.c'
    c_set['source_subst'] = 'C_SOURCES ='
    c_set['inc_endswith'] = '.h'
    c_set['inc_subst'] = 'C_INCLUDES ='
    c_set['first'] = True
    c_set['relpath_stored'] = ''
    ctx.append(c_set)

    asm_set = {}
    asm_set['source_endswith'] = '.s'
    asm_set['source_subst'] = 'ASM_SOURCES ='
    asm_set['inc_endswith'] = '.inc'
    asm_set['inc_subst'] = 'AS_INCLUDES ='
    asm_set['first'] = True
    asm_set['relpath_stored'] = ''
    ctx.append(asm_set)

    # .cproject file
    try:
        tree = xml.etree.ElementTree.parse(ac6_cproject_path)
    except Exception as e:
        sys.stderr.write("Unable to parse SW4STM32 .cproject file: {}. Error: {}\n".format(
            ac6_cproject_path, str(e)))
        sys.exit(C2M_ERR_PROJECT_FILE)
    root = tree.getroot()

    # C_INCLUDES
    include_nodes = root.findall(
        './/tool[@superClass="fr.ac6.managedbuild.tool.gnu.cross.c.compiler"]/option[@valueType="includePath"]/listOptionValue')
    # print "Include Nodes", include_nodes
    for include_node in include_nodes:
        c_include_str = include_node.attrib.get('value')
        if len(c_include_str .strip()) > 0:
            # remove one ../ because this isn't made in a dir
            inc_dir = c_include_str[c_include_str.find('/')+1:]
            include_dir = fix_path_caps(inc_dir, proj_folder_path)
            if (include_dir):

                c_set['inc_subst'] += ' -I' + include_dir
            else:
                print("Can't Find Include Dir", inc_dir)

    # ASM_INCLUDES
    include_nodes = root.findall(
        './/tool[superClass="fr.ac6.managedbuild.tool.gnu.cross.assembler"]/option[@valueType="includePath"]/listOptionValue')
    # print "Include Nodes", include_nodes
    for include_node in include_nodes:
        inc_str = include_node.attrib.get('value')
        if len(inc_str.strip()) > 0:
            include_dir = fix_path_caps(inc_str, proj_folder_path)
            if include_dir:
                asm_set['inc_subst'] += ' -I' + include_dir
            else:
                print("Can't Find Include Dir", include_dir)

    # MCU
    mcu_node = root.find(
        './/toolChain/option[@superClass="fr.ac6.managedbuild.option.gnu.cross.mcu"][@name="Mcu"]')
    try:
        mcu_str = mcu_node.attrib.get('value')
    except Exception as e:
        sys.stderr.write(
            "Unable to find target MCU node. Error: {}\n".format(str(e)))
        sys.exit(C2M_ERR_PROJECT_FILE)
    for mcu_regex_pattern, cflags in list(mcu_regex_to_cflags_dict.items()):
        if re.match(mcu_regex_pattern, mcu_str):
            cflags_subst = cflags
            ld_subst = cflags
            break
    for mcu_regex_pattern, float_abi in list(mcu_regex_to_float_abi_dict.items()):
        if re.match(mcu_regex_pattern, mcu_str):
            float_abi_subs = float_abi
            break
    for mcu_regex_pattern, libs in list(mcu_regex_to_libs_dict.items()):
        if re.match(mcu_regex_pattern, mcu_str):
            std_lib_subs = libs
            break

    else:
        sys.stderr.write("Unknown MCU: {}\n".format(mcu_str))
        sys.stderr.write(
            "Please contact author for an update of this utility.\n")
        sys.stderr.exit(C2M_ERR_NEED_UPDATE)

    # AS symbols
    as_defs_subst = 'AS_DEFS ='

    # C symbols
    c_defs_subst = 'C_DEFS ='
    c_def_node_list = root.findall(
        './/tool/option[@valueType="definedSymbols"]/listOptionValue')
    for c_def_node in c_def_node_list:
        c_def_str = c_def_node.attrib.get('value')
        if c_def_str:
            c_defs_subst += ' -D{}'.format(c_def_str)

    # Link script
    ld_script_node_list = root.find(
        './/tool/option[@superClass="fr.ac6.managedbuild.tool.gnu.cross.c.linker.script"]')
    try:
        ld_script_path = ld_script_node_list.attrib.get('value')
    except Exception as e:
        sys.stderr.write(
            "Unable to find link script. Error: {}\n".format(str(e)))
        sys.exit(C2M_ERR_PROJECT_FILE)
    ld_script_name = os.path.basename(ld_script_path)
    ld_script_subst = 'LDSCRIPT = {}'.format(ld_script_name)

    # Get libraries
    lib_dir_nodes = root.findall(
        './/tool/option[@superClass="gnu.c.link.option.paths"]/listOptionValue')
    library_dirs = []
    # print lib_dir_nodes

    for n in lib_dir_nodes:
        indir_name = n.attrib.get('value')
        indir_name = os.path.sep.join(indir_name.split(os.path.sep)[1:])
        dir_name = fix_path_caps(indir_name, proj_folder_path)
        if dir_name:
            library_dirs.append("-L " + dir_name)
        else:
            print("Library Path Not found", indir_name)
    # except Exception:
    #    pass
    librarys = root.findall(
        './/tool/option[@superClass="gnu.c.link.option.libs"]/listOptionValue')
    proj_libs = []
    for lib in librarys:
        lib_name = lib.attrib.get('value')
        proj_libs.append("-l "+fixup_lib_names(lib_name))
    # .project file

    try:
        tree = xml.etree.ElementTree.parse(ac6_project_path)
    except Exception as e:
        sys.stderr.write("Unable to parse SW4STM32 .project file: {}. Error: {}\n".format(
            ac6_project_path, str(e)))
        sys.exit(C2M_ERR_PROJECT_FILE)
    proj_root = tree.getroot()
    for location_str in ['.//linkedResources/link/location', './/linkedResources/link/locationURI']:
        link_nodes = proj_root.findall(location_str)
        for node in link_nodes:
            filename = node.text
            updirs = filename.split('-')[1]
            updirs = int(updirs)
            updirs_str = ("../")*updirs
            in_filename = filename.replace(
                'PARENT-%i-PROJECT_LOC/' % updirs, updirs_str)
    #        dirs = int(s) for s in str.split() if s.isdigit()
            filename = fix_path_caps(in_filename, proj_folder_path)
            if filename:
                print(filename)
                if filename.endswith('.c'):
                    c_set['source_subst'] += " "+filename
                if filename.endswith('.s'):
                    asm_set['source_subst'] += " " + filename
            else:
                print("Can't find", in_filename)
    makefile_str = makefile_template.substitute(
        APP_NAME=proj_name,
        MCU=cflags_subst,
        FLOAT_ABI=float_abi_subs,
        LD_STD_LIBS=std_lib_subs,
        LD_LIB_DIRS=" ".join(library_dirs),
        LD_LIBS=" ".join(proj_libs),
        LLVM_PATH=LLVM_PATH,
        GCC_PATH=GCC_PATH,
        LDMCU=ld_subst,
        C_SOURCES=c_set['source_subst'],
        ASM_SOURCES=asm_set['source_subst'],
        AS_DEFS=as_defs_subst,
        AS_INCLUDES=asm_set['inc_subst'],
        C_DEFS=c_defs_subst,
        C_INCLUDES=c_set['inc_subst'],
        LDSCRIPT=ld_script_subst)

    makefile_path = os.path.join(proj_folder_path, 'Makefile')
    try:
        with open(makefile_path, 'wb') as f:
            f.write(makefile_str)
    except EnvironmentError as e:
        sys.stderr.write(
            "Unable to write Makefile: {}. Error: {}\n".format(makefile_path, str(e)))
        sys.exit(C2M_ERR_IO)

    sys.stdout.write("Makefile created: {}\n".format(makefile_path))

    sys.exit(C2M_ERR_SUCCESS)


def fix_path(p):
    return re.sub(r'^..(\\|/)..(\\|/)..(\\|/)', '', p.replace('\\', os.path.sep))


if __name__ == '__main__':
    main()
