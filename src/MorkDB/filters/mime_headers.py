# Copyright 2010 Kevin Goodsell

import re
import warnings
import quopri

from filterbase import Filter

class DecodeMimeHeaders(Filter):
    '''Filter to decode RFC 2047 MIME headers.'''
    def __init__(self, order):
        self.mork_filter_order = order

    def add_options(self, parser):
        parser.add_option('--mime-headers', action='store_true',
            help='decode MIME email headers '
                 '(e.g.: =?iso-8859-1?Q?=A1Hola,_se=F1or!?=)')

    def process(self, db, opts):
        if not opts.mime_headers:
            return

        for (row_namespace, rowid, row) in db.rows.items():
            headers = self._header_fields.get(row_namespace)
            if headers is None:
                # This kind of row has no headers to decode.
                continue

            for (column, value) in row.items():
                if column not in headers:
                    # This is not a decodable header.
                    continue

                row[column] = self._decode_header(value)

    # This must contain all field that need to be converted.
    _header_fields = {
        # {'row namespace' : set(['column name'])}
        'ns:msg:db:row:scope:msgs:all' : set(['recipients', 'sender',
                                              'subject', 'ccList', 'replyTo']),
        'ns:msg:db:row:scope:threads:all' : set(['threadSubject']),
    }

    def _decode_string(self, charset, encoding, encoded):
        if encoding == 'q':
            # Direct decoding doesn't handle RFC 2047's underscores-for-spaces
            # rule, so use quopri.
            encoded = quopri.decodestring(encoded, True)
        elif encoding == 'b':
            encoded = encoded.decode('base64')
        else:
            raise ValueError('Unknown MIME header encoding: %r' % encoding)

        return encoded.decode(charset)

    # This is based on ecre from email.header.
    _encoded_matcher = re.compile(r'''
        =\?                   # literal =?
        (?P<charset>[^?]*?)   # non-greedy up to the next ? is the charset
        \?                    # literal ?
        (?P<encoding>[qb])    # either a "q" or a "b", case insensitive
        \?                    # literal ?
        (?P<encoded>.*?)      # non-greedy up to the next ?= is the encoded string
        \?=                   # literal ?=
        (\s+(?==\?))?         # consume the space between two encoded strings
    ''', re.VERBOSE | re.IGNORECASE | re.MULTILINE)

    def _replacer(self, m):
        charset = m.group('charset')
        encoding = m.group('encoding')
        encoded = m.group('encoded')

        try:
            return self._decode_string(charset, encoding.lower(), encoded)
        # There doesn't seem to be a more specific exception that can be used
        # here.
        except Exception, e:
            val = m.group()
            warnings.warn('mime_headers decoding failed for %r (%s)' % (val, e))
            return val

    def _decode_header(self, value):
        return self._encoded_matcher.sub(self._replacer, value)

mime_headers_filter = DecodeMimeHeaders(4400)
