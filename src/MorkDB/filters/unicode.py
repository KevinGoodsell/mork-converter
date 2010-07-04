# Copyright 2010 Kevin Goodsell

import warnings

from filterbase import Filter

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

class DecodeCharacters(Filter):
    def __init__(self, order):
        self.mork_filter_order = order

    def add_options(self, parser):
        parser.add_option('--no-decoding', action='store_true',
            help="don't decode character encodings")

    def process(self, db, opts):
        if opts.no_decoding:
            return

        self._filter(db)

    # Decoders for specific fields where guessing won't work.
    _decoders = {
        # {('row namespace', 'column name') : decoder_function}
        ('ns:history:db:row:scope:history:all', 'Name') : _utf16_decoder,
        ('ns:formhistory:db:row:scope:formhistory:all', 'Name') :
            _utf16_decoder,
        ('ns:formhistory:db:row:scope:formhistory:all', 'Value') :
            _utf16_decoder,
    }

    _byte_order_encodings = {
        # Byte order tags from the ByteOrder meta-table field.
        'llll' : 'utf_16_le',
        'LE'   : 'utf_16_le',
        'BBBB' : 'utf_16_be',
        'BE'   : 'utf_16_be',
    }

    def _filter(self, db):
        for (table_namespace, table_id, table) in db.tables.items():
            # Set the default utf-16 encoding, then check for a specific
            # ByteOrder in the meta-table.
            utf16_encoding = 'utf_16_le'

            metatable = db.metaTables.get((table_namespace, table_id))
            if metatable and 'ByteOrder' in metatable.columnNames():
                byte_order = metatable['ByteOrder']
                utf16_encoding = self._byte_order_encodings.get(byte_order)
                assert utf16_encoding is not None, \
                    'Unknown byte order: %s' % byte_order

            self._filter_table(table, utf16_encoding)

    def _filter_table(self, table, utf16_encoding):
        for (row_namespace, row_id, row) in table:
            for (column, value) in row.items():
                if isinstance(value, unicode):
                    continue

                decoder = self._decoders.get((row_namespace, column),
                                             _default_decoder)
                try:
                    new_value = decoder(value, utf16_encoding)
                except Exception, e:
                    import pdb
                    pdb.set_trace()
                    warnings.warn('failed to get encoding for row namespace '
                                  '%s, column %s (%r)' %
                                  (row_namespace, column, value))
                else:
                    row[column] = new_value

decoding_filter = DecodeCharacters(2010)
