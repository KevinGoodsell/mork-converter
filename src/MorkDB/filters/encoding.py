# Copyright 2010 Kevin Goodsell

# This file is part of mork-converter.
#
# mork-converter is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License Version 2 as published
# by the Free Software Foundation.
#
# mork-converter is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mork-converter.  If not, see <http://www.gnu.org/licenses/>.

import warnings
import codecs
import re
import optparse

from filterbase import Filter

# Decoders:

def _decode_utf8(opts, byte_order, row_namespace, column, value):
    '''
    Decoder that attempts UTF-8, and gives up on error.
    '''
    try:
        return value.decode('utf-8')
    except UnicodeError:
        return None

_known_utf16 = set([
    ('ns:history:db:row:scope:history:all', 'Name'),
    ('ns:formhistory:db:row:scope:formhistory:all', 'Name'),
    ('ns:formhistory:db:row:scope:formhistory:all', 'Value'),
])
def _decode_known_utf16(opts, byte_order, row_namespace, column, value):
    '''
    Decoder for fields known to be UTF-16.
    '''
    if (row_namespace, column) not in _known_utf16:
        return None

    if byte_order in ('BE', 'BBBB'):
        codec = 'utf-16-be'
    elif byte_order in ('LE', 'llll'):
        codec = 'utf-16-le'
    else:
        assert False, 'Invalid byte order: %r' % byte_order

    return value.decode(codec)

_control_matcher = re.compile(ur'[\x80-\x9f]')
def _decode_iso_8859(opts, byte_order, row_namespace, column, value):
    '''
    Decoder that uses one of the ISO-8859 encodings, and fails if the result
    contains C1 control characters (based on the assumption that this means
    it's the wrong characer set).
    '''
    # Skip ISO-8859 decoding if user asks or if bytes are found that would
    # decode as control characters.
    if opts.iso_8859 == '' or _control_matcher.search(value):
        return None

    try:
        return value.decode('iso-8859-%s' % opts.iso_8859)
    except UnicodeError:
        return None

def _decode_final(opts, byte_order, row_namespace, column, value):
    '''
    Last-ditch decoder.
    '''
    try:
        return value.decode(opts.fallback_charset)
    except UnicodeError:
        return None

class DecodeCharacters(Filter):
    def __init__(self, order):
        self.mork_filter_order = order

    def add_options(self, parser):
        decode_group = optparse.OptionGroup(parser, 'Field Decoding Options')
        decode_group.add_option('-b', '--byte-order',
            choices=['big', 'little', 'b', 'l'],
            help='default byte order for decoding multi-byte fields (big or '
                 'little)')
        iso_parts = self._iso_8895_parts()
        decode_group.add_option('-i', '--iso-8859', metavar='N',
            choices=iso_parts + [''],
            help='select the ISO-8859 character set for fields in the input '
                 'file (default: 1, available: %s)' % ', '.join(iso_parts))
        decode_group.add_option('-f', '--fallback-charset', metavar='CHARSET',
            help='select the character set used for field decoding when all '
                 'others fail (default: windows-1252)')

        parser.add_option_group(decode_group)
        parser.set_defaults(iso_8859='1', fallback_charset='windows-1252')

    def process(self, db, opts):
        for (table_namespace, table_id, table) in db.tables.items():
            byte_order = self._find_byte_order(db, opts, table_namespace,
                                               table_id)
            self._filter_table(opts, table, byte_order)

    def _iso_8895_parts(self):
        result = []
        for part in range(1, 17):
            try:
                codecs.lookup('iso-8859-%d' % part)
            except LookupError:
                continue

            result.append(str(part))

        return result

    def _find_byte_order(self, db, opts, table_namespace, table_id):
        '''
        Determine byte order by meta-table data or options. Failing that,
        fall back on guessing.
        '''
        byte_order = None
        metatable = db.meta_tables.get((table_namespace, table_id))
        if metatable:
            try:
                byte_order = metatable['ByteOrder']
            except KeyError:
                pass

        if byte_order is None and opts.byte_order:
            if opts.byte_order in ('b', 'big'):
                byte_order = 'BE'
            else:
                byte_order = 'LE'

        if byte_order is None:
            table = db.tables.get((table_namespace, table_id))
            byte_order = self._guess_byte_order(opts, table)

        return byte_order

    def _guess_byte_order(self, opts, table):
        counts = {'BE' : 0, 'LE' : 0}
        # Check each row and column, testing for likely byte order
        for (row_namespace, row_id, row) in table:
            for (column, value) in row.items():
                if (row_namespace, column) not in _known_utf16:
                    # Not a UTF-16 field
                    continue

                warnings.warn('guessing byte order, consider using -b option')

                # Fewest unique Most Significant Bytes is a reasonable guess
                be_msbs = set(value[::2]) # even indices
                le_msbs = set(value[1::2]) # odd indices
                if len(be_msbs) < len(le_msbs):
                    counts['BE'] += 1
                elif len(be_msbs) > len(le_msbs):
                    counts['LE'] += 1

        counts = [(count, val) for (val, count) in counts.items()]
        counts.sort()
        return counts[-1][1]

    def _filter_table(self, opts, table, byte_order):
        for (row_namespace, row_id, row) in table:
            for (column, value) in row.items():
                if isinstance(value, unicode):
                    continue

                row[column] = self._decode_field(opts, byte_order,
                                                 row_namespace, column, value)

    _decoders = [
        _decode_known_utf16,
        _decode_utf8,
        _decode_iso_8859,
        _decode_final,
    ]

    def _decode_field(self, opts, byte_order, row_namespace, column, value):
        for decoder in self._decoders:
            decoded_val = decoder(opts, byte_order, row_namespace, column,
                                  value)
            if decoded_val is not None:
                return decoded_val

        assert False, 'failed to decode %r' % value

new_decoding_filter = DecodeCharacters(2010)

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
