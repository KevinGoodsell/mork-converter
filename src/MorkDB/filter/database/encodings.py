# Copyright (c) 2009 Kevin Goodsell

import warnings

import MorkDB.filter.util as util

_MORK_DATABASE_FILTER = True

usage = []
description = 'Convert fields to UTF-8'

# Decoders
#
# These take a utf16_encoding value that is based on the byte order in the
# meta-table. It is only used for UTF-16 decoding.

def _utf16_decoder(value, utf16_encoding):
    return value.decode(utf16_encoding)

def _default_decoder(value, utf16_encoding):
    try:
        return value.decode('utf-8')
    except:
        pass

    return value.decode('latin-1')

# All non-UTF-8 fields have to show up here.
_decoders = {
    # {('row namespace', 'column name') : decoder_funcion}
    ('ns:history:db:row:scope:history:all', 'Name') : _utf16_decoder,
    ('ns:formhistory:db:row:scope:formhistory:all', 'Name') : _utf16_decoder,
    ('ns:formhistory:db:row:scope:formhistory:all', 'Value') : _utf16_decoder,
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
        # Set the default utf-16 encoding, then check for a specific ByteOrder
        # in the meta-table.
        utf16_encoding = 'utf_16_le'

        metaTable = db.metaTables.get((tableNamespace, tableId))
        if metaTable and 'ByteOrder' in metaTable.columnNames():
            byteOrder = metaTable['ByteOrder']
            utf16_encoding = _byteOrderEncodings.get(byteOrder)
            assert utf16_encoding is not None, \
                'Unknown byte order: %s' % byteOrder

        _filterTable(table, utf16_encoding)

def _filterTable(table, utf16_encoding):
    for (rowNamespace, rowId, row) in table:
        for (column, value) in row.items():
            if isinstance(value, unicode):
                continue

            decoder = _decoders.get((rowNamespace, column), _default_decoder)
            try:
                new_value = decoder(value, utf16_encoding)
            except:
                warnings.warn('failed to UTF-8 encode rowNamespace %s, '
                              'column %s (%r)' % (rowNamespace, column, value))
            else:
                row[column] = new_value
