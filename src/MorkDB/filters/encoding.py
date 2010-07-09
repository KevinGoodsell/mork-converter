# Copyright 2010 Kevin Goodsell

import warnings
import codecs

from filterbase import Filter

# Character decoders. Unused parameters are to keep the interface consistent.
def _default_decoder(value, opts, byte_order):
    return value.decode(opts.def_encoding)

def _utf8_fallback_decoder(value, opts, byte_order):
    try:
        return value.decode('utf-8')
    except UnicodeError:
        return _default_decoder(value, opts, byte_order)

_utf16_byte_order_decoders = {
    # Byte order tags from the ByteOrder meta-table field.
    'llll' : codecs.getdecoder('utf-16-le'),
    'LE'   : codecs.getdecoder('utf-16-le'),
    'BBBB' : codecs.getdecoder('utf-16-be'),
    'BE'   : codecs.getdecoder('utf-16-be'),
}
def _utf16_decoder(value, opts, byte_order):
    if byte_order is None:
        # Default to little-endian because that's how it works in test files.
        byte_order = 'LE'

    decoder = _utf16_byte_order_decoders.get(byte_order)
    assert decoder is not None, \
        'Unknown byte order: %s' % byte_order

    return decoder(value)[0]

class DecodeCharacters(Filter):
    '''
    Converts fields to unicode objects. Tries to interpret using known
    encodings, or tries to guess, or uses the --def-encoding option.
    '''
    def __init__(self, order):
        self.mork_filter_order = order

    def add_options(self, parser):
        parser.add_option('-d', '--def-encoding', metavar='ENC',
            help="use ENC as the character encoding when no other encoding "
                 "can be determined")
        parser.add_option('--only-def-encoding', action='store_true',
            help="interpret all fields using --def-encoding, don't test "
                 "to determine the character encoding")

        parser.set_defaults(def_encoding='latin-1')

    def process(self, db, opts):
        for (table_namespace, table_id, table) in db.tables.items():
            byte_order = None
            metatable = db.meta_tables.get((table_namespace, table_id))
            if metatable:
                try:
                    byte_order = metatable['ByteOrder']
                except KeyError:
                    pass

            self._filter_table(table, byte_order, opts)

    # Decoders for specific fields where guessing won't work.
    _decoders = {
        # {('row namespace', 'column name') : decoder_function}
        ('ns:history:db:row:scope:history:all', 'Name') :
            _utf16_decoder,
        ('ns:formhistory:db:row:scope:formhistory:all', 'Name') :
            _utf16_decoder,
        ('ns:formhistory:db:row:scope:formhistory:all', 'Value') :
            _utf16_decoder,
    }

    def _filter_table(self, table, byte_order, opts):
        for (row_namespace, row_id, row) in table:
            for (column, value) in row.items():
                if isinstance(value, unicode):
                    continue

                if opts.only_def_encoding:
                    decoder = _default_decoder
                else:
                    decoder = self._decoders.get((row_namespace, column))
                    if decoder is None:
                        decoder = _utf8_fallback_decoder

                row[column] = decoder(value, opts, byte_order)

decoding_filter = DecodeCharacters(2010)

# Support for writing encoded streams while taking care of things like
# Byte-Order Marks.
class EncodingStream(object):
    def __init__(self, output_encoding, stream):
        (encoder, bom) = self._fix_encoding(output_encoding)

        self.encoder = codecs.getencoder(encoder)
        self.stream = stream

        self.stream.write(bom)

    @classmethod
    def open(cls, output_encoding, filename):
        f = open(filename, 'w')
        return cls(output_encoding, f)

    def write(self, s):
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
