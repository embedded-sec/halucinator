# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a
# non-exclusive license for use of this work by or on behalf of the U.S.
# Government. Export of this data may require a license from the United States
# Government.


from struct import unpack


def get_sp_and_entry(binary_filename):
    '''
    Gets the initial stack pointer and entry point from the filename
    It assumes the passed file is loaded/aliased to address 0x00000000
    Args: 
        binary_filename(string):   path to file to open, assumes binary format

    Returns:
        sp(int), entry(int):  Stack pointer and entry point of board
    '''
    with open(binary_filename, 'rb') as bin_file:
        sp, entry = unpack('<II', bin_file.read(8))

    return sp, entry
