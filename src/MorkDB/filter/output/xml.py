# Copyright (c) 2009 Kevin Goodsell

# Output filter for writing Mork databases in XML format. This is also a basic
# introduction to writing output filters using the tools in output.util.
import MorkDB.filter.util as util

# REQUIRED: All output filters should include _MORK_OUTPUT_FILTER. The value
# doesn't matter, just the presence of the variable.
_MORK_OUTPUT_FILTER = True

# REQUIRED: All output filters should have a description. It is displayed in
# the help output, unless it evaluates as false.
description = 'Simple XML output filter'

# REQUIRED: All output filters have a usage. This is a sequence of items,
# and each item is a sequence of two items. Effectively this is a sequence of
# (argumentName, argumentDescription) pairs. util.Argument behaves as a
# sequence of two items, but can also have a 'converter', which is used in
# util.convertArgs to convert the argument text (a string) to whatever type
# is desired. When not supplied, the argument just remains a string.
usage = [
    util.Argument('out', 'Name to use for output file (default: mork.xml)'),
]

# REQUIRED: The output function does the real work. Its arguments are a
# MorkDatabase instance and a dict of arguments with argument names for the
# keys and argument text for the values.
def output(db, args):
    # convertArgs uses the names in 'usage' to check the validity of the
    # arguments and uses the converters in 'usage' to convert argument text
    # to more useful types.
    #
    # This does NOT check for required arguments. If there are required args,
    # check for them specifically.
    args = util.convertArgs(usage, args)
    return _outputHelper(db, **args)

_indentStr = '    '

def _outputHelper(db, out='mork.xml'):
    f = open(out, 'w')
    print >> f, '<?xml version="1.0"?>'
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

    for (rowNamespace, rowId, row) in table:
        _writeRow(f, rowNamespace, rowId, row, indent + 1)

    if meta is not None:
        _writeMetaTable(f, meta, indent + 1)

    print >> f, '%s</table>' % indentStr

def _writeMetaTable(f, meta, indent):
    indentStr = _indentStr * indent
    print >> f, '%s<metatable>' % indentStr

    for (column, value) in meta.cells.items():
        _writeCell(f, column, value, indent + 1)

    for (namespace, oid, row) in meta.rows:
        _writeRow(f, namespace, oid, row, indent + 1)

    print >> f, '%s</metatable>' % indentStr

def _writeRow(f, namespace, oid, row, indent):
    indentStr = _indentStr * indent
    print >> f, '%s<row namespace=%s id=%s>' % (indentStr,
        _formatAttribute(namespace), _formatAttribute(oid))

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
