# Copyright 2010 Kevin Goodsell
#
# Mork output filter for Comma-Separated Values.

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

import re
import os
import sys

from filterbase import Filter
from encoding import EncodingStream

class CsvOutput(Filter):
    '''
    Filter that writes Mork databases in Comma-Separated Values format.
    '''
    def __init__(self, order):
        self.mork_filter_order = order

    def add_options(self, parser):
        parser.add_option('--csv', dest='out_format', action='store_const',
            const='csv', help='output comma-separated values (CSV)')
        parser.add_option('--single-file', action='store_true',
            help='for CSV output, use one file instead of a directory '
                 'containing a file for each table')

        parser.set_defaults(out_format='csv')

    def process(self, db, opts):
        if opts.out_format != 'csv':
            return

        name = opts.outname or '-'
        # Write a single file if it's asked for, or if the output is stdout.
        single = opts.single_file or name == '-'

        if single:
            writer = _SingleFileWriter(opts, name)
        else:
            writer = _MultiFileWriter(opts, name)

        for (namespace, oid, table) in db.tables.items():
            writer.write_table(table, namespace, oid)
            meta = db.meta_tables.get((namespace, oid))
            if meta is not None:
                writer.write_meta_table(meta, namespace, oid)

        writer.close()

csv_filter = CsvOutput(10100)

class _TableWriter(object):
    '''
    _TableWriter is an abstraction to make it easy to write to either one file
    per table or one file for all tables, with a header to delimit them.
    Derived classes override _new_table(), _new_metatable(), and maybe close().
    '''
    def __init__(self, opts):
        self.opts = opts

    def _new_table(self, namespace, oid):
        '''
        Override in derived classes. Returns the file handle to write to.
        '''
        raise NotImplementedError()

    def _new_metatable(self, namespace, oid):
        '''
        Override in derived classes. Returns the file handle to write to.
        '''
        raise NotImplementedError()

    def _write_rows(self, f, rows, headers):
        for (row_namespace, rowid, row) in rows:
            # construct each output row by fetching the values corresponding to
            # each header (and using an empty string if there is none), then
            # prepending the row namespace and id.
            values = [row.get(header, '') for header in headers]
            values = [row_namespace, rowid] + values
            print >> f, self._format_csv_row(values)

    def write_table(self, table, namespace, oid):
        import MorkDB.morkdb as morkdb
        assert isinstance(table, morkdb.MorkTable)
        f = self._new_table(namespace, oid)

        # skip over empty tables:
        if len(table) == 0:
            return
        # construct and output the table header line by fetching and sorting
        # the headers, then prepending headers for namespace and id:
        headers = list(table.column_names())
        headers.sort()
        print >> f, self._format_csv_row(['namespace', 'id'] + headers)

        self._write_rows(f, table, headers)

    def write_meta_table(self, metatable, namespace, oid):
        import MorkDB.morkdb as morkdb
        assert isinstance(metatable, morkdb.MorkMetaTable)
        f = self._new_metatable(namespace, oid)

        # Since meta-tables contain both individual cells and rows, there's
        # some tweaking to put it all into a CSV table. The cells get crammed
        # into a single row. The rows have namespace and id at the front just
        # like in normal tables, but for metatables with no rows these extra
        # columns are suppressed.

        # skip empty meta-tables:
        if len(metatable.cells) + len(metatable.rows) == 0:
            return

        # extra_headers is for the rows, extra_values for the cells row.
        # These have to kept even for the number of columns to be equal.
        if len(metatable.rows) == 0:
            extra_headers = []
            extra_values = []
        else:
            extra_headers = ['namespace', 'id']
            extra_values = ['', '']

        # Header line
        headers = list(metatable.column_names())
        headers.sort()
        print >> f, self._format_csv_row(extra_headers + headers)

        # Output cells
        values = [metatable.cells.get(header, '') for header in headers]
        print >> f, self._format_csv_row(extra_values + values)

        # Output rows
        self._write_rows(f, metatable.rows, headers)

    def open(self, filename):
        '''
        Simple helper function to use EncodingStream.
        '''
        if filename == '-':
            return EncodingStream(self.opts.out_encoding, sys.stdout)
        else:
            return EncodingStream.open(self.opts.out_encoding, filename)

    def close(self):
        pass

    _needs_quotes = re.compile(r'''
      [,\r\n"] # Characters that force double-quoting
    | (^[ \t]) # Leading whitespace
    | ([ \t]$) # Trailing whitespace
    ''', re.VERBOSE)

    def _format_csv_value(self, value):
        '''
        Format value as as CSV field.
        '''
        match = self._needs_quotes.search(value)
        if match:
            # Add surrounding double-quotes and double internal double-quotes.
            value = '"%s"' % value.replace('"', '""')

        return value

    def _format_csv_row(self, items):
        return ','.join(self._format_csv_value(item) for item in items)

class _SingleFileWriter(_TableWriter):
    def __init__(self, opts, outname):
        _TableWriter.__init__(self, opts)

        self.outname = outname
        self.fp = self.open(outname)

    def _new_table(self, namespace, oid, prefix=''):
        print >> self.fp, '-' * 70
        print >> self.fp, '%sTABLE %s :: %s' % (prefix, namespace, oid)
        print >> self.fp, '-' * 70
        return self.fp

    def _new_metatable(self, namespace, oid):
        return self._new_table(namespace, oid, 'META-')

    def close(self):
        if self.fp is not None and self.outname != '-':
            self.fp.close()
            self.fp = None

class _MultiFileWriter(_TableWriter):
    def __init__(self, opts, dirname):
        _TableWriter.__init__(self, opts)

        self.dirname = dirname
        self.current_file = None
        os.mkdir(dirname)

    def _new_table(self, namespace, oid, postfix=''):
        self.close()
        filename = '%s-%s%s' % (namespace, oid, postfix)
        self.current_file = self.open(os.path.join(self.dirname, filename))
        return self.current_file

    def _new_metatable(self, namespace, oid):
        return self._new_table(namespace, oid, '-meta')

    def close(self):
        if self.current_file is not None:
            self.current_file.close()
            self.current_file = None
