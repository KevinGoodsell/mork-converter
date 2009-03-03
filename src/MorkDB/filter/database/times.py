# Copyright (c) 2009 Kevin Goodsell
import time

import MorkDB.filter.util as util

_MORK_DATABASE_FILTER = True

description = 'Convert dates/times to a readable format'

usage = [
    util.Argument('format',
        'Time format as a strftime format string (default: %c)'),
]

def _convertText(text, format, base=10, divisor=1):
    if text == '0':
        return '0'

    seconds = int(text, base) / divisor
    t = time.localtime(seconds)

    return time.strftime(format, t)

def _convertSeconds(text, format)
    return _convertText(text, format)

def _convertHexSeconds(text, format):
    return _convertText(text, format, base=16)

def _convertMicroSeconds(text, format):
    return _convertText(text, format, divisor=1000000)

_tableTimeFields = {
    # { 'row namespace' : {'field name' : covertFunction} }
    'ns:addrbk:db:row:scope:card:all' : {
        'LastModifiedDate' : _convertHexSeconds,
    },

    'ns:history:db:row:scope:history:all' : {
        'LastVisitDate'  : _convertMicroSeconds,
        'FirstVisitDate' : _convertMicroSeconds,
    },

    'ns:msg:db:row:scope:dbfolderinfo:all' : {
        'folderDate' : _convertHexSeconds,
        'MRUTime'    : _convertSeconds,
    },

    'ns:msg:db:row:scope:msgs:all' : {
        'date' : _convertHexSeconds,
    },

    'm' : {
        'threadNewestMsgDate' : _convertHexSeconds,
    },
}

def filter(db, args):
    args = util.convertArgs(usage, args)
    _filterHelper(db, **args)

def _filterHelper(db, format='%c'):
    for (rowNamespace, rowId, row) in db.rows.items():
        fields = _tableTimeFields.get(rowNamespace)
        if fields is None:
            continue

        for (column, value) in row.items():
            converter = fields.get(column)
            if converter is None:
                continue

            row[column] = converter(value, format)
