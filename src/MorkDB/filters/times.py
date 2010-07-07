# Copyright 2010 Kevin Goodsell

import time

from filterbase import Filter

# Filter to convert cryptic time/date fields to a nicer format.
class ConvertTimes(Filter):
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
            fields = self._table_time_fields.get(row_namespace)
            if fields is None:
                # No known times in this type of row.
                continue

            for (column, value) in row.items():
                converter = fields.get(column)
                if converter is None:
                    # Not a time column, as far as we know.
                    continue

                row[column] = converter(value, format)

    @classmethod
    def _convert_text(cls, text, format, base=10, divisor=1):
        # 0 is a common value, and obviously doesn't repressent a valid time.
        if text == '0':
            return '0'

        seconds = int(text, base) / divisor
        t = time.localtime(seconds)

        return time.strftime(format, t)

    @classmethod
    def _convert_seconds(cls, text, format):
        return cls._convert_text(text, format)

    @classmethod
    def _convert_hex_seconds(cls, text, format):
        return cls._convert_text(text, format, base=16)

    @classmethod
    def _convert_micro_seconds(cls, text, format):
        return cls._convert_text(text, format, divisor=1000000)

ConvertTimes._table_time_fields = {
    # { 'row namespace' : {'field name' : covert_function} }
    'ns:addrbk:db:row:scope:card:all' : {
        'LastModifiedDate' : ConvertTimes._convert_hex_seconds,
    },

    'ns:history:db:row:scope:history:all' : {
        'LastVisitDate'  : ConvertTimes._convert_micro_seconds,
        'FirstVisitDate' : ConvertTimes._convert_micro_seconds,
    },

    'ns:msg:db:row:scope:dbfolderinfo:all' : {
        'folderDate' : ConvertTimes._convert_hex_seconds,
        'MRUTime'    : ConvertTimes._convert_seconds,
    },

    'ns:msg:db:row:scope:folders:all' : {
        'MRUTime' : ConvertTimes._convert_seconds,
    },

    'ns:msg:db:row:scope:msgs:all' : {
        'date' : ConvertTimes._convert_hex_seconds,
    },

    'm' : {
        'threadNewestMsgDate' : ConvertTimes._convert_hex_seconds,
    },
}

convert_times_filter = ConvertTimes(5000)
