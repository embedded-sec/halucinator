# Copyright 2018 National Technology & Engineering Solutions of Sandia, LLC 
# (NTESS). Under the terms of Contract DE-NA0003525 with NTESS, there is a 
# non-exclusive license for use of this work by or on behalf of the U.S. 
# Government. Export of this data may require a license from the United States 
# Government.


from pycparser import c_parser, c_ast, parse_file, plyparser
from collections import OrderedDict
import hexyaml
import yaml
import os
# Derived from example in pycparser
# https://github.com/eliben/pycparser/blob/master/examples/func_defs.py 

class FuncDeclMapper(c_ast.NodeVisitor):
    def __init__(self):
        super(FuncDeclMapper,self).__init__()
        self.descriptors = dict()
    

    def visit_FuncDecl(self, node):
        '''
            Visits each function declaration generates a config for a 
            RegisterLogger.  It determines the return type, and arguments to 
            log based of the function declaration
        '''
       
        intercept_config = {}
        try:
            intercept_config['function'] = get_function_name(node)
            intercept_config['class'] = 'RegisterLogger'
        except AttributeError as e:
            print e
            import pdb; pdb.set_trace()

        class_args = {}

        # Determine Return Type
        if is_type_void(node):
            class_args['ret_value'] = None
        else:
            class_args['ret_value'] = 0
       
        # Determine Args to log
        reg_list = []
        for i, p in enumerate(node.args.params):
            #import pdb; pdb.set_trace()
            try:
                ty = get_final_type(p)
                #print p
                if i > 3:
                    #TODO Look up calling convention if num args is more than 4
                    break
                elif is_type_void(p):
                    continue
                else:
                    reg_list.append('r'+str(i))
            except AttributeError:
                import pdb; pdb.set_trace()
        class_args['regs'] = reg_list
        intercept_config['class_args'] = class_args
        self.descriptors[intercept_config['function']] = intercept_config

        #print('%s at %s' % (node.type.declname, node.coord))

def get_function_name(node):
    '''
        Gets the function name from ast node
    '''
    if type(node.type) == c_ast.PtrDecl:
        return node.type.type.declname
    else:
        return node.type.declname


def is_type_void(node):
    '''
        Checks if the nodes type is void
        Return True if void
    '''
    ty = node.type
    if type(ty) == c_ast.IdentifierType and 'void' in ty.names:
        return True
    else:
        return False


def get_final_type(node):
    try:
        if hasattr(node.type,'type'):
            return get_final_type(node.type)
        else:
            return node.type
    except AttributeError:
        import pdb; pdb.set_trace()

def parse_header_file(header_file):
    '''
        Maps the header file to intercepts configs 
    '''
    try:
        ast = parse_file(header_file)
        v = FuncDeclMapper()
        v.visit(ast) 
    except plyparser.ParseError:
        return None
    return v.descriptors
    

def write_intercept_config(intercepts, output_filename):
    '''
        Writes intercept config file for set of parsed headers
        Args:
            intercepts(dict):       Dictionary of intercepts for each function
            output_filename(str):   Name of file to write intercepts to
    '''
    config = [intercepts[key] for key in sorted(intercepts.keys())]
    with open(output_filename, 'wb') as outfile:
        yaml.safe_dump(config, outfile)


if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('-f', '--filename',
                    help='Input filename to run parser over')
    p.add_argument('-d', '--dir',
                    help='Input directory to run parser over')
    p.add_argument('-o', '--output_file', required=True,
                    help='Filename to write output configuration to')                    

    args = p.parse_args()
    if args.dir:
        failed_files = []
        for f in sorted(os.listdir(args.dir)):
            intercepts = {}
            if f.endswith('.h'):
                filename = os.path.join(args.dir,f)
                print "Parsing: ", filename
                i = parse_header_file(filename)
                if i != None:
                    intercepts.update(i)
                else:
                    failed_files.append(filename)
                write_intercept_config(intercepts, args.output_file)
        if len(failed_files) > 0:
            print "Failed Files:\n", '\n'.join(failed_files)
    elif args.filename:
        i = parse_header_file(args.filename)
        if i != None:
            write_intercept_config(i, args.output_file)
    else:
        print "Either -f (filename) or -d (dir) required"
        p.print_usage()