import re
import os

import output.util as util
import morkdb

usage = [
    util.Argument('outname', 'Name to use for output directory (or file, if'
        ' singlefile is used)'),
    util.Argument('singlefile', 'Output no a single file instead of one file'
        ' per table', util.convertBool),
]

def output(db, args):
    args = util.convertArgs(usage, args)
    return _outputHelper(db, **args)

def _outputHelper(db, outname='csvout', singlefile=False):
    if singlefile:
        f = open(outname, 'w')
    else:
        os.mkdir(outname)

    for (namespace, oid, table) in db.tables.items():
        if singlefile:
            print >> f, '-' * 70
            print >> f, 'TABLE %s :: %s' % (namespace, oid)
            print >> f, '-' * 70
        else:
            filename = '%s-%s' % (namespace, oid)
            f = open(os.path.join(outname, filename), 'w')

        _writeCsv(f, table)

_needsQuotes = re.compile(r'''
  [,\r\n"] # Characters that force double-quoting
| (^[ \t]) # Leading and ...
| ([ \t]$) # ...trailing whitespace
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

def _writeCsv(f, table):
    assert isinstance(table, morkdb.MorkTable)

    headers = list(table.columnNames())
    headers.sort()

    headerline = ','.join(_formatCsvValue(header) for header in headers)
    print >> f, headerline

    for row in table:
        values = [row.get(header, '') for header in headers]
        line = ','.join(_formatCsvValue(value) for value in values)
        print >> f, line
