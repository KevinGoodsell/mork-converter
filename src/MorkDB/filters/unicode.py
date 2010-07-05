# Copyright 2010 Kevin Goodsell

import warnings
import codecs

from filterbase import Filter

# Decoders
#
# These take a utf16_encoding value that is based on the byte order in the
# meta-table. It is only used for UTF-16 decoding.

def _utf16_decoder(value, utf16_encoding):
    return value.decode(utf16_encoding)

def _default_decoder(value, utf16_encoding):
    return value.decode('utf-8')

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
                except:
                    pass
                else:
                    row[column] = new_value

decoding_filter = DecodeCharacters(2010)

# Support for re-encoding str objects on output while directly encoding
# unicode objects.

class EncodingStream(object):
    def __init__(self, default_encoding, output_encoding, stream):
        (decoder, unused) = self._fix_encoding(default_encoding)
        (encoder, bom) = self._fix_encoding(output_encoding)

        self.decoder = codecs.getdecoder(decoder)
        self.encoder = codecs.getencoder(encoder)
        self.stream = stream

        self.stream.write(bom)

    @classmethod
    def open(cls, default_encoding, output_encoding, filename):
        f = open(filename, 'w')
        return cls(default_encoding, output_encoding, f)

    def write(self, s):
        if isinstance(s, str):
            (s, consumed) = self.decoder(s)

        (s, consumed) = self.encoder(s)
        self.stream.write(s)

    def __getattr__(self, name):
        return getattr(self.stream, name)

    _boms = {
        'utf-16-be' : codecs.BOM_UTF16_BE,
        'utf-16-le' : codecs.BOM_UTF16_LE,
        'utf-32-be' : codecs.BOM_UTF32_BE,
        'utf-32-le' : codecs.BOM_UTF32_LE,
    }
    def _fix_encoding(self, encoding):
        normalized = codecs.lookup(encoding).name

        if normalized == 'utf-8-sig':
            return ('utf-8', codecs.BOM_UTF8)

        if normalized == 'utf-16':
            if codecs.BOM_UTF16 == codecs.BOM_UTF16_BE:
                replacement = 'utf-16-be'
            else:
                replacement = 'utf-16-le'
        elif normalized == 'utf-32':
            if codecs.BOM_UTF32 == codecs.BOM_UTF32_BE:
                replacement = 'utf-32-be'
            else:
                replacement = 'utf-32-le'
        else:
            replacement = normalized

        return (replacement, self._boms.get(replacement, ''))
