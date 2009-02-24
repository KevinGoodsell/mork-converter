import output.util as util

_MORK_OUTPUT_FILTER = True

usage = [
    util.Argument('outname', 'Name to use for output file'),
]

def output(db, args):
    args = util.convertArgs(usage, args)
    return _outputHelper(db, **args)

_indentStr = '    '

def _outputHelper(db, outname='mork.xml'):
    f = open(outname, 'w')
    print >> f, '<morkxml>'

    for (namespace, oid, table) in db.tables.items():
        meta = db.metaTables.get((namespace, oid))
        _writeTable(f, namespace, oid, table, meta)

    print >> f, '</morkxml>'
    f.close()

def _writeTable(f, namespace, oid, table, meta=None, indent=1):
    indentStr = _indentStr * indent
    print >> f, '%s<table namespace=%s id=%s>' % (indentStr,
        _formatAttribute(namespace), _formatAttribute(oid))

    for row in table.values():
        _writeRow(f, row, indent + 1)

    if meta is not None:
        _writeMetaTable(f, meta, indent + 1)

    print >> f, '%s</table>' % indentStr

def _writeMetaTable(f, meta, indent):
    indentStr = _indentStr * indent
    print >> f, '%s<metatable>' % indentStr

    for column in meta.columnNames():
        value = meta[column]
        _writeCell(f, column, value, indent + 1)

    print >> f, '%s</metatable>' % indentStr

def _writeRow(f, row, indent):
    indentStr = _indentStr * indent
    print >> f, '%s<row>' % indentStr

    for (column, value) in row.items():
        _writeCell(f, column, value, indent + 1)

    print >> f, '%s</row>' % indentStr

def _writeCell(f, column, value, indent):
    indentStr = _indentStr * indent
    print >> f, '%s<cell column=%s>%s</cell>' % (indentStr,
        _formatAttribute(column), _formatElementText(value))

def _formatAttribute(value):
    return '"%s"' % value.replace('&', '&amp;').replace('"', '&quot;')

def _formatElementText(value):
    return value.replace('&', '&amp;').replace('<', '&lt;').replace('>',
        '&gt;')
