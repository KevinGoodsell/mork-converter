# Copyright 2010 Kevin Goodsell

import os
import sys
import re

_module_blacklist = re.compile(r'''
      ^\.          # starts with dot
    | ^__          # starts with __
''', re.VERBOSE)

def _find_modules():
    # Use __path__[0] to find module files, __name__ for importing
    directory = __path__[0]
    package = __name__

    dir_entries = os.listdir(directory)
    modules = [name.split('.', 1)[0] for name in dir_entries
               if not _module_blacklist.search(name)]

    for m in modules:
        module_name = '%s.%s' % (package, m)
        # This is based on the discussion of __import__ in the Python
        # Library Reference.
        try:
            __import__(module_name)
        except ImportError:
            pass
        else:
            yield sys.modules[module_name]

def enumerate_filters():
    filters = set()
    for m in _find_modules():
        for (name, obj) in vars(m).items():
            if hasattr(obj, 'mork_filter_order') and \
               obj.mork_filter_order >= 0:
                filters.add(obj)

    filters = [(obj.mork_filter_order, obj) for obj in filters]
    filters.sort()
    return [obj for (order, obj) in filters]
