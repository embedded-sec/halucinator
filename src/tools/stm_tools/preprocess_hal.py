# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC 
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a 
# non-exclusive license for use of this work by or on behalf of the U.S. 
# Government. Export of this data may require a license from the United States 
# Government.

import subprocess
from os import path
import os
import re

STM_DRIVER_PATH = path.expanduser('~/projects/HALucinator/Zoo/STM/F4/STM32Cube_FW_F4_V1.21.0/Drivers')

# TODO  Change to YAML so can be used for any HAL
# Paths that need to be included to enable compilation
INCLUDES = ['-I' + path.join(STM_DRIVER_PATH, 'STM32F4xx_HAL_Driver/Inc'),
            '-I'+ path.join(STM_DRIVER_PATH,'CMSIS/Include/'),
            '-I'+ path.join(STM_DRIVER_PATH, 'CMSIS/Device/ST/STM32F4xx/Include/'),
            '-I'+ path.expanduser('~/projects/HALucinator/avatar-devices/3rd_party/pycparser-release_v2.18/utils/fake_libc_include/')]

# Macros that need defined on commandline
DEFINES = ['-DSTM32F479xx']
 
PREPROCESS_CMD = ['arm-none-eabi-gcc', '-E', '-nostdinc' ] 
#PREPROCESS_CMD = ['arm-none-eabi-gcc' ] 
  
def remove_unsupported_code(infile, outfile):
    '''
        Removes C language features not supported by pycparser:
            __attributes__
            __asm
    '''
    remove_regexs = [r'__attribute__\s*\(\s*\(\s*\S*\s*\)\s*\)',
                     r'__asm.*\);']  # __asm directives
    #TODO Just extend pycparser to support them

    with open(infile,'rt') as infile_fd:
        contents = infile_fd.read()
        for regex in remove_regexs:
            contents = re.sub(regex, '', contents)

    with open(outfile, 'wt') as outfile_fd:
        outfile_fd.write(contents)





def preprocess_header(infile, outfile):
    '''
        preprocesses the file using arm-none-eabi-gcc, This then enables it to 
        to be parsed by pycparser
        Args:
            infile:  Input header file to be parsed
            outfile:  Name of file to write result to
    '''

    cmd = list(PREPROCESS_CMD)
    cmd.extend(DEFINES)
    cmd.extend(INCLUDES)
    cmd.append(infile)
    cmd.extend(['-o' + outfile])

    #print "Running: ", " ".join(cmd)

    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        print "FAILED: ", infile

    print "SUCCESS: ", infile


def process_dir(indir, outdir):
    '''
        Preprocesses all the files in indir, outputing the preprocessed files 
        to outdir
    '''
    if not os.path.isdir(outdir):
        if not os.path.exists(outdir):
            print "Making Dir: ", outdir
            os.makedirs(outdir)
        else:
            print "ERROR:  Invalid outdir, exists but no directory"
            exit()

    for f in os.listdir(indir):
        if f.endswith('.h'):
            infile = path.join(indir,f)
            outfile = path.join(outdir,f)
            preprocess_header(infile, outfile)
            if os.path.exists(outfile):
                remove_unsupported_code(outfile, outfile)


if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('-d', '--indir', required=True,
                    help="Directory of header files to preprocess")
    p.add_argument('-o', '--outdir',required=True,
                    help='Name of directory to write preprocessed files to')
    args = p.parse_args()

    process_dir(args.indir, args.outdir)