import re
import os

import MorkDB.output.util as util

_MORK_OUTPUT_FILTER = True

usage = [
    util.Argument('outname', 'Name to use for output directory (or file, if'
        ' singlefile is used)'),
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

    def writeTable(self, table, namespace, oid):
        import MorkDB.morkdb as morkdb
        assert isinstance(table, morkdb.MorkTable)
        f = self._newTable(namespace, oid)

        headers = list(table.columnNames())
        if len(headers) == 0:
            return
        headers.sort()
        print >> f, _formatCsvRow(headers)

        for row in table.values():
            values = [row.get(header, '') for header in headers]
            print >> f, _formatCsvRow(values)

    def writeMetaTable(self, metatable, namespace, oid):
        import MorkDB.morkdb as morkdb
        assert isinstance(metatable, morkdb.MorkMetaTable)
        f = self._newMetaTable(namespace, oid)

        headers = list(metatable.columnNames())
        if len(headers) == 0:
            return
        headers.sort()
        print >> f, _formatCsvRow(headers)

        values = [metatable[header] for header in headers]
        print >> f, _formatCsvRow(values)

    def close(self):
        pass

class _SingleFileWriter(_TableWriter):
    def __init__(self, outname):
        _TableWriter.__init__(self)

        self.fp = open(outname, 'w')

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
        self.currentFile = open(os.path.join(self.dirname, filename), 'w')
        return self.currentFile

    def _newMetaTable(self, namespace, oid):
        return self._newTable(namespace, oid, '-meta')

    def close(self):
        if self.currentFile is not None:
            self.currentFile.close()
            self.currentFile = None

def _outputHelper(db, outname='csvout', singlefile=False):
    if singlefile:
        writer = _SingleFileWriter(outname)
    else:
        writer = _MultiFileWriter(outname)

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
