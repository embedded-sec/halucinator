# Copyright 2019 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.


from functools import wraps


def bp_handler(arg):
    '''
        @bp_handler decorator

        arg: either the function if used as @bp_handler
            or a list of intercepting functions e.g., @bp_handler(['F1','F2'])

    '''
    if callable(arg):
        # Handles @bp_handler with out args allows any function
        arg.is_bp_handler = True
        return arg
    else:
        # Handles @bp_handler(['F1','F2'])
        def bp_decorator(func):
            func.bp_func_list = arg
            return func
        return bp_decorator


class BPHandler(object):

    def register_handler(self, qemu, addr, func_name):
        canidate_methods = [getattr(self.__class__, x) for x in dir(
            self.__class__) if hasattr(getattr(self.__class__, x), 'bp_func_list')]
        for canidate in canidate_methods:
            if func_name in canidate.bp_func_list:
                return canidate

        error_str = "%s does not have bp_handler for %s" % \
                    (self.__class__.__name__, func_name)
        raise ValueError(error_str)
