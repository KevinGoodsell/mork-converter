# Copyright (c) 2009 Kevin Goodsell
import os

import MorkDB.moduleTools as modtools

class _DatabaseFilterPool(modtools.ModulePool):
    def _validateModule(self, name, module):
        if not hasattr(module, '_MORK_DATABASE_FILTER'):
            raise modtools.BadModule('not a valid database filter: %s' % name)

dbFilters = _DatabaseFilterPool(os.path.dirname(os.path.abspath(__file__)),
                                'MorkDB.filter')
