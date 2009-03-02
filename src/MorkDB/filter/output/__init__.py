# Copyright (c) 2009 Kevin Goodsell
import os

import MorkDB.moduleTools as modtools

class _OutputFilterPool(modtools.ModulePool):
    def _validateModule(self, name, module):
        if not hasattr(module, '_MORK_OUTPUT_FILTER'):
            raise modtools.BadModule('not a valid output filter: %s' % name)

filters = _OutputFilterPool(os.path.dirname(os.path.abspath(__file__)),
                            'MorkDB.filter.output')
