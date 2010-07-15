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

import time

from filterbase import Filter

def _convert_textual_time(text, format, base=10, divisor=1):
    # 0 is a common value, and obviously doesn't repressent a valid time.
    if text == '0':
        return '0'

    seconds = int(text, base) / divisor
    t = time.localtime(seconds)

    return time.strftime(format, t)

def _convert_seconds(text, format):
    return _convert_textual_time(text, format)

def _convert_hex_seconds(text, format):
    return _convert_textual_time(text, format, base=16)

def _convert_microseconds(text, format):
    return _convert_textual_time(text, format, divisor=1000000)

class ConvertTimes(Filter):
    '''Filter to convert cryptic time/date fields to a nicer format.'''
    def __init__(self, order):
        self.mork_filter_order = order

    def add_options(self, parser):
        parser.add_option('-t', '--time', action='store_true',
            help='translate time/date fields to human-readable format')
        parser.add_option('--time-format', metavar='FORMAT',
            help='use FORMAT as the strftime format for times/dates '
                 '(default: %c, implies -t)')

    def process(self, db, opts):
        if not opts.time and not opts.time_format:
            return

        # get the format, or use the default
        format = opts.time_format or '%c'

        for (row_namespace, rowid, row) in db.rows.items():
            fields = self._time_converters.get(row_namespace)
            if fields is None:
                # No known times in this type of row.
                continue

            for (column, value) in row.items():
                converter = fields.get(column)
                if converter is None:
                    # Not a time column, as far as we know.
                    continue

                row[column] = converter(value, format)

    _time_converters = {
        # { 'row namespace' : {'field name' : convert_function} }
        'ns:addrbk:db:row:scope:card:all' : {
            'LastModifiedDate' : _convert_hex_seconds,
        },

        'ns:history:db:row:scope:history:all' : {
            'LastVisitDate'  : _convert_microseconds,
            'FirstVisitDate' : _convert_microseconds,
        },

        'ns:msg:db:row:scope:dbfolderinfo:all' : {
            'folderDate' : _convert_hex_seconds,
            'MRUTime'    : _convert_seconds,
        },

        'ns:msg:db:row:scope:folders:all' : {
            'MRUTime' : _convert_seconds,
        },

        'ns:msg:db:row:scope:msgs:all' : {
            'date'         : _convert_hex_seconds,
            'dateReceived' : _convert_hex_seconds,
        },

        'm' : {
            'threadNewestMsgDate' : _convert_hex_seconds,
        },
    }

convert_times_filter = ConvertTimes(5000)
