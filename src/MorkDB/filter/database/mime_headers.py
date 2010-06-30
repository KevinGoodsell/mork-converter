# Copyright (c) 2009 Kevin Goodsell

import re
import warnings

import MorkDB.filter.util as util

_MORK_DATABASE_FILTER = True

usage = []
description = 'Decode MIME email headers (e.g.: =?iso-8859-1?Q?=A1Hola,_se=F1or!?=)'

# This must contain all field that need to be converted.
_header_fields = {
    # {'row namespace' : set(['column name'])}
    'ns:msg:db:row:scope:msgs:all' : set(['recipients', 'sender', 'subject',
                                          'ccList']),
    'ns:msg:db:row:scope:threads:all' : set(['threadSubject']),
}

def filter(db, args):
    args = util.convertArgs(usage, args)
    _filter_helper(db, **args)

def _filter_helper(db):
    for (rowNamespace, rowId, row) in db.rows.items():
        headers = _header_fields.get(rowNamespace)
        if headers is None:
            # This kind of row has no headers to decode.
            continue

        for (column, value) in row.items():
            if column not in headers:
                # This is not a decodable header.
                continue

            row[column] = _decode_header(value)

def _decode_string(charset, encoding, encoded):
    if encoding == 'q':
        encoded = encoded.decode('quotedprintable')
    elif encoding == 'b':
        encoded = encoded.decode('base64')
    else:
        raise ValueError('Unknown MIME header encoding: %r' % encoding)

    as_unicode = encoded.decode(charset)
    return as_unicode.encode('utf-8')

# This is based on ecre from email.header.
_encoded_matcher = re.compile(r'''
    =\?                   # literal =?
    (?P<charset>[^?]*?)   # non-greedy up to the next ? is the charset
    \?                    # literal ?
    (?P<encoding>[qb])    # either a "q" or a "b", case insensitive
    \?                    # literal ?
    (?P<encoded>.*?)      # non-greedy up to the next ?= is the encoded string
    \?=                   # literal ?=
''', re.VERBOSE | re.IGNORECASE | re.MULTILINE)

def _replacer(m):
    charset = m.group('charset')
    encoding = m.group('encoding')
    encoded = m.group('encoded')

    try:
        return _decode_string(charset, encoding.lower(), encoded)
    # There doesn't seem to be a more specific exception that can be used here.
    except Exception, e:
        val = m.group()
        warnings.warn('mime_headers decoding failed for %r (%s)' % (val, e))
        return val

def _decode_header(value):
    return _encoded_matcher.sub(_replacer, value)
