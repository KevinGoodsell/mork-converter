# Copyright 2010 Kevin Goodsell

# This file is part of mork-converter.
#
# mork-converter is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License Version 2 as published
# by the Free Software Foundation.
#
# mork-converter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mork-converter.  If not, see <http://www.gnu.org/licenses/>.

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

_filters = None
def enumerate_filters():
    global _filters

    if _filters is None:
        filters = set()
        for m in _find_modules():
            for (name, obj) in vars(m).items():
                if hasattr(obj, 'mork_filter_order') and \
                   obj.mork_filter_order >= 0:
                    filters.add(obj)

        _filters = [(obj.mork_filter_order, obj) for obj in filters]
        _filters.sort()

    return _filters

def list_filters():
    return [filt for (order, filt) in enumerate_filters()]
