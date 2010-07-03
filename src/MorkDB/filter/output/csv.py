# Copyright (c) 2009 Kevin Goodsell
import re
import os
import codecs

import MorkDB.filter.util as util

_MORK_OUTPUT_FILTER = True

description = 'Comma-Separated Values output filter'

usage = [
    util.Argument('out', 'Name to use for output directory (or file, if'
                  ' singlefile is used, default: csvout)'),
    util.Argument('singlefile', 'Output no a single file instead of one file'
                  ' per table', util.convertBool),
]

def output(db, args):
    args = util.convertArgs(usage, args)
    return _outputHelper(db, **args)

class _TableWriter(object):
    def _newTable(self, namespace, oid):
        raise NotImplementedError()

    def _newMetaTable(self, namespace, oid):
        raise NotImplementedError()

    def _writeRows(self, f, rows, headers):
        for (rowNamespace, rowId, row) in rows:
            values = [row.get(header, '') for header in headers]
            values = [rowNamespace, rowId] + values
            print >> f, _formatCsvRow(values)

    def writeTable(self, table, namespace, oid):
        import MorkDB.morkdb as morkdb
        assert isinstance(table, morkdb.MorkTable)
        f = self._newTable(namespace, oid)

        if len(table) == 0:
            return
        headers = list(table.columnNames())
        headers.sort()
        print >> f, _formatCsvRow(['namespace', 'id'] + headers)

        self._writeRows(f, table, headers)

    def writeMetaTable(self, metatable, namespace, oid):
        import MorkDB.morkdb as morkdb
        assert isinstance(metatable, morkdb.MorkMetaTable)
        f = self._newMetaTable(namespace, oid)

        if len(metatable.cells) + len(metatable.rows) == 0:
            return

        if len(metatable.rows) == 0:
            extraHeaders = []
            extraValues = []
        else:
            extraHeaders = ['namespace', 'id']
            extraValues = ['', '']

        # Header line
        headers = list(metatable.columnNames())
        headers.sort()
        print >> f, _formatCsvRow(extraHeaders + headers)

        # Output cells
        values = [metatable.cells.get(header, '') for header in headers]
        print >> f, _formatCsvRow(extraValues + values)

        # Output rows
        self._writeRows(f, metatable.rows, headers)

    def close(self):
        pass

class _SingleFileWriter(_TableWriter):
    def __init__(self, outname):
        _TableWriter.__init__(self)

        self.fp = codecs.open(outname, 'w', encoding='utf-8')

    def _newTable(self, namespace, oid, prefix=''):
        print >> self.fp, '-' * 70
        print >> self.fp, '%sTABLE %s :: %s' % (prefix, namespace, oid)
        print >> self.fp, '-' * 70
        return self.fp

    def _newMetaTable(self, namespace, oid):
        return self._newTable(namespace, oid, 'META-')

    def close(self):
        if self.fp is not None:
            self.fp.close()
            self.fp = None

class _MultiFileWriter(_TableWriter):
    def __init__(self, dirname):
        _TableWriter.__init__(self)

        self.dirname = dirname
        self.currentFile = None
        os.mkdir(dirname)

    def _newTable(self, namespace, oid, postfix=''):
        self.close()
        filename = '%s-%s%s' % (namespace, oid, postfix)
        self.currentFile = codecs.open(os.path.join(self.dirname, filename),
                                       'w', encoding='utf-8')
        return self.currentFile

    def _newMetaTable(self, namespace, oid):
        return self._newTable(namespace, oid, '-meta')

    def close(self):
        if self.currentFile is not None:
            self.currentFile.close()
            self.currentFile = None

def _outputHelper(db, out='csvout', singlefile=False):
    if singlefile:
        writer = _SingleFileWriter(out)
    else:
        writer = _MultiFileWriter(out)

    for (namespace, oid, table) in db.tables.items():
        writer.writeTable(table, namespace, oid)
        meta = db.metaTables.get((namespace, oid))
        if meta is not None:
            writer.writeMetaTable(meta, namespace, oid)

    writer.close()

_needsQuotes = re.compile(r'''
  [,\r\n"] # Characters that force double-quoting
| (^[ \t]) # Leading whitespace
| ([ \t]$) # Trailing whitespace
''', re.VERBOSE)

def _formatCsvValue(value):
    '''
    Format value as as CSV field.
    '''
    match = _needsQuotes.search(value)
    if match:
        # Add surrounding double-quotes and double internal double-quotes.
        value = '"%s"' % value.replace('"', '""')

    return value

def _formatCsvRow(items):
    return ','.join(_formatCsvValue(item) for item in items)
