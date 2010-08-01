# Copyright 2010 Kevin Goodsell
#
# Simple Mork database filters.

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

from filterbase import Filter

class StripEmptyCells(Filter):
    '''
    Filter to remove cells with empty values, producing more compact output.
    '''
    def __init__(self, order):
        self.mork_filter_order = order

    def add_options(self, parser):
        parser.add_option('-s', '--strip-empty', action='store_true',
            help="don't include empty cells in the output")

    def process(self, db, opts):
        if not opts.strip_empty:
            return

        for (row_namespace, row_id, row) in db.rows.items():
            for (col, val) in row.items():
                if not val:
                    del row[col]

strip_empty_filter = StripEmptyCells(4400)

class StripMetaTables(Filter):
    '''
    Filter to remove meta-tables, since they aren't necessarily useful to see.
    '''
    def __init__(self, order):
        self.mork_filter_order = order

    def add_options(self, parser):
        parser.add_option('-m', '--strip-meta', action='store_true',
            help="don't include meta-tables in the output")

    def process(self, db, opts):
        if not opts.strip_meta:
            return

        db.meta_tables.clear()

# Meta-tables might be necessary for other filters, so they get removed late.
strip_metatables_filter = StripMetaTables(9900)
