# Copyright (c) 2009 Kevin Goodsell

import MorkDB.filter.util as util

_MORK_DATABASE_FILTER = True

usage = []
description = 'Convert UTF-16 fields to UTF-8'

# All UTF-16 fields have to show up here.
_utf16Fields = {
    # {'now namespace' : set(['column name']) }
    'ns:history:db:row:scope:history:all' : set(['Name']),
    'ns:formhistory:db:row:scope:formhistory:all' : set(['Name', 'Value']),
}

_byteOrderEncodings = {
    # Byte order tags from the ByteOrder meta-table field.
    'llll' : 'utf_16_le',
    'LE'   : 'utf_16_le',
    'BBBB' : 'utf_16_be',
    'BE'   : 'utf_16_be',
}

def filter(db, args):
    args = util.convertArgs(usage, args)
    _filterHelper(db, **args)

def _filterHelper(db):
    for (tableNamespace, tableId, table) in db.tables.items():
        # Set the default encoding, then check for a specific ByteOrder in
        # the meta-table.
        encoding = 'utf_16_le'

        metaTable = db.metaTables.get((tableNamespace, tableId))
        if metaTable and 'ByteOrder' in metaTable.columnNames():
            byteOrder = metaTable['ByteOrder']
            encoding = _byteOrderEncodings.get(byteOrder)
            assert encoding is not None, 'Unknown byte order: %s' % byteOrder

        _filterTable(table, encoding)

def _filterTable(table, encoding):
    for (rowNamespace, rowId, row) in table:
        fields = _utf16Fields.get(rowNamespace)
        if fields is None:
            # This type of row has no UTF-16 fields (as far as I know)
            continue

        for (column, value) in row.items():
            if column not in fields:
                # This column is not in UTF-16 (as far as I know)
                continue

            row[column] = value.decode(encoding).encode('utf-8')
