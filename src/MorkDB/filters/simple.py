# Copyright 2010 Kevin Goodsell
#
# Simple Mork database filters.

from filterbase import Filter

class StripEmptyCells(Filter):
    def __init__(self, order):
        self.mork_filter_order = order

    def add_options(self, parser):
        parser.add_option('-s', '--strip-empty', action='store_true',
            help='strip empty cells from the database')

    def process(self, db, opts):
        if not opts.strip_empty:
            return

        for (row_namespace, row_id, row) in db.rows.items():
            for (col, val) in row.items():
                if not val:
                    del row[col]

strip_empty_filter = StripEmptyCells(100)

class StripMetaTables(Filter):
    def __init__(self, order):
        self.mork_filter_order = order

    def add_options(self, parser):
        parser.add_option('-m', '--strip-meta', action='store_true',
            help='strip meta-tables from the database')

    def process(self, db, opts):
        if not opts.strip_meta:
            return

        db.metaTables.clear()

# Meta-tables might be necessary for other filters, so they get removed late.
strip_metatables_filter = StripMetaTables(9900)
