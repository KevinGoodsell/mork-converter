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

class FieldInfo(object):
    '''
    Holds all the info a decoder might need.
    '''
    def __init__(self, db, opts, table_namespace, table_id):
        self.db = db
        self.opts = opts
        self.table_namespace = table_namespace
        self.table_id = table_id

        self.row_namespace = None
        self.column = None
        self.value = None

        self._byte_order = None

    def set_value(self, row_namespace, column, value):
        self.row_namespace = row_namespace
        self.column = column
        self.value = value

    def table(self):
        return self.db.tables[self.table_namespace, self.table_id]

    def byte_order(self):
        if self._byte_order is None:
            self._byte_order = self._find_byte_order()

        return self._byte_order

    def _find_byte_order(self):
        '''
        Determine byte order by meta-table data or options. Failing that,
        fall back on guessing.
        '''
        byte_order = None
        metatable = self.db.meta_tables.get((self.table_namespace,
                                             self.table_id))
        if metatable:
            try:
                byte_order = metatable['ByteOrder']
            except KeyError:
                pass

        if byte_order is None and self.opts.byte_order:
            if self.opts.byte_order in ('b', 'big'):
                byte_order = 'BE'
            else:
                byte_order = 'LE'

        if byte_order is None:
            byte_order = self._guess_byte_order()

        return byte_order

    def _guess_byte_order(self):
        table = self.db.tables.get((self.table_namespace, self.table_id))
        be_count = 0
        le_count = 0
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
                    be_count += 1
                elif len(be_msbs) > len(le_msbs):
                    le_count += 1

        if be_count > le_count:
            return 'BE'
        else:
            return 'LE'

# Decoders:

def _decode_from_opts(field):
    '''
    Decoder that uses user-supplied encodings for specific fields.
    '''
    if isinstance(field.opts.force_encoding, list):
        # convert to dict:
        kv = [((row_ns, col), enc) for (row_ns, col, enc)
              in field.opts.force_encoding]
        field.opts.force_encoding = dict(kv)

    encoding = field.opts.force_encoding.get((field.row_namespace,
                                              field.column))
    if encoding is None:
        return None

    return field.value.decode(encoding)

def _decode_utf8(field):
    '''
    Decoder that attempts UTF-8, and gives up on error.
    '''
    try:
        return field.value.decode('utf-8')
    except UnicodeError:
        return None

_known_utf16 = set([
    ('ns:history:db:row:scope:history:all', 'Name'),
    ('ns:formhistory:db:row:scope:formhistory:all', 'Name'),
    ('ns:formhistory:db:row:scope:formhistory:all', 'Value'),
])
def _decode_known_utf16(field):
    '''
    Decoder for fields known to be UTF-16.
    '''
    if (field.row_namespace, field.column) not in _known_utf16:
        return None

    byte_order = field.byte_order()
    if byte_order in ('BE', 'BBBB'):
        codec = 'utf-16-be'
    elif byte_order in ('LE', 'llll'):
        codec = 'utf-16-le'
    else:
        assert False, 'Invalid byte order: %r' % byte_order

    return field.value.decode(codec)

_control_matcher = re.compile(ur'[\x80-\x9f]')
def _decode_iso_8859(field):
    '''
    Decoder that uses one of the ISO-8859 encodings, and fails if the result
    contains C1 control characters (based on the assumption that this means
    it's the wrong characer set).
    '''
    # Skip ISO-8859 decoding if user asks or if bytes are found that would
    # decode as control characters.
    if field.opts.iso_8859 == '' or _control_matcher.search(field.value):
        return None

    try:
        return field.value.decode('iso-8859-%s' % field.opts.iso_8859)
    except UnicodeError:
        return None

def _decode_final(field):
    '''
    Last-ditch decoder.
    '''
    try:
        return field.value.decode(field.opts.fallback_charset)
    except UnicodeError:
        return None

class DecodeCharacters(Filter):
    '''
    Filter to convert fields to unicode using user-specified options, known
    encodings, UTF-8, ISO 8859 char sets, or a last-ditch char set.
    '''
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
        decode_group.add_option('-f', '--fallback-charset', metavar='ENCODING',
            help='select the character set used for field decoding when all '
                 'others fail (default: windows-1252)')
        decode_group.add_option('--force-encoding',
            metavar='ROW_NAMESPACE COLUMN ENCODING', nargs=3, action='append',
            help='force the use of ENCODING for specified fields')

        parser.add_option_group(decode_group)
        parser.set_defaults(iso_8859='1', fallback_charset='windows-1252',
                            force_encoding=[])

    def process(self, db, opts):
        for (table_namespace, table_id, table) in db.tables.items():
            field = FieldInfo(db, opts, table_namespace, table_id)
            self._filter_table(field, table)

    def _iso_8895_parts(self):
        result = []
        for part in range(1, 17):
            try:
                codecs.lookup('iso-8859-%d' % part)
            except LookupError:
                continue

            result.append(str(part))

        return result

    def _filter_table(self, field, table):
        for (row_namespace, row_id, row) in table:
            for (column, value) in row.items():
                if isinstance(value, unicode):
                    continue

                field.set_value(row_namespace, column, value)
                row[column] = self._decode_field(field)

    _decoders = [
        _decode_from_opts,
        _decode_known_utf16,
        _decode_utf8,
        _decode_iso_8859,
        _decode_final,
    ]

    def _decode_field(self, field):
        for decoder in self._decoders:
            decoded_val = decoder(field)
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
