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

import optparse
import warnings

from filterbase import Filter
import converters

_converters = {
    # General converters first.
    'none'               : converters.NullConverter(),
    'integer-hex'        : converters.IntHex(),
    'integer-hex-signed' : converters.SignedInt32(),
    'boolean-integer'    : converters.BoolInt(),
    'boolean-any'        : converters.BoolAnyVal(),
    'seconds'            : converters.Seconds(),
    'seconds-hex'        : converters.SecondsHex(),
    'seconds-guess-base' : converters.SecondsGuessBase(),
    'microseconds'       : converters.Microseconds(),

    # Specific converters second.
    'hier-delim'            : converters.HierDelim(),
    'message-flags'         : converters.MsgFlags(),
    'imap-flags'            : converters.ImapFlags(),
    'sort-columns'          : converters.SortColumns(),
    'last-purge-time'       : converters.LastPurgeTime(),
    'message-folder-flags'  : converters.MsgFolderFlags(),
    'card-type'             : converters.CardType(),
    'prefer-mail-format'    : converters.PreferMailFormat(),
    'acl-flags'             : converters.AclFlags(),
    'box-flags'             : converters.BoxFlags(),
    'current-view'          : converters.CurrentView(),
    'retain-by'             : converters.RetainBy(),
    'view-type'             : converters.ViewType(),
    'view-flags'            : converters.ViewFlags(),
    'sort-type'             : converters.SortType(),
    'sort-order'            : converters.SortOrder(),
    'priority'              : converters.Priority(),
    'remote-content-policy' : converters.RemoteContentPolicy(),
}

# The big dictionary of field converters.
#
# Note: ns:addrbk, ns:history, ns:formhistory are pretty obvious, but ns:msg
# is used for both Mail Summary Files and Folder Caches. However, Folder Caches
# have :scope:folders and Mail Summary Files have several scopes, none of which
# are 'folders'.
#
# Source references are included for some of the simpler converters. The more
# specific converters include source references in their class definition.
# References use TB for Thunderbird, FF for Firefox, and a version number in
# addition to a path in the source tree and sometimes a function name.

_conversions = {
    # Address Book Fields (ns:addrbk).
    'ns:addrbk:db:row:scope:card:all' : {
        # TB3.0.5:mailnews/addrbook/src/nsAddrDatabase.h AddAllowRemoteContent
        'AllowRemoteContent' : 'boolean-integer',
        'CardType'           : 'card-type',
        # TB3.0.5:mailnews/addrbook/src/nsAddrDatabase.cpp
        # AddRowToDeletedCardsTable
        'LastModifiedDate'   : 'seconds-guess-base',
        # TB3.0.5:mailnews/addrbook/src/nsAddrDatabase.h AddPopularityIndex
        'PopularityIndex'    : 'integer-hex',
        'PreferMailFormat'   : 'prefer-mail-format',
    },
    'ns:addrbk:db:row:scope:list:all' : {
        # TB3.0.5:mailnews/addrbook/src/nsAddrDatabase.cpp GetListAddressTotal
        'ListTotalAddresses' : 'integer-hex',
    },

    # History Fields (ns:history).
    'ns:history:db:row:scope:history:all' : {
        # Tokens are created in
        # FF2.0.0.20:toolkit/components/history/src/nsGlobalHistory.cpp
        # CreateTokens. AddNewPageToDatabase in the same file is a good
        # reference for these.
        'FirstVisitDate' : 'microseconds',
        'LastVisitDate'  : 'microseconds',
        'Hidden'         : 'boolean-any',
        'Typed'          : 'boolean-any',
    },

    # Folder Cache Fields (ns:msg:db:row:scope:folders:).
    # Folder caches seem to share a lot of attributes with
    # ns:msg:db:row:scope:dbfolderinfo from .msf files.
    'ns:msg:db:row:scope:folders:all' : {
        'LastPurgeTime'     : 'last-purge-time',
        # Defined in TB:3.0.5:mailnews/base/public/msgCore.h, used
        # in mailnews/base/util/nsMsgDBFolder.cpp
        'MRUTime'           : 'seconds',
        'aclFlags'          : 'acl-flags',
        'boxFlags'          : 'box-flags',
        'hierDelim'         : 'hier-delim',

        # The remaining items are all from
        # TB3.0.5:mailnews/base/util/nsMsgDBFolder.cpp
        'flags'             : 'message-folder-flags',
        'totalMsgs'         : 'integer-hex-signed',
        'totalUnreadMsgs'   : 'integer-hex-signed',
        'pendingUnreadMsgs' : 'integer-hex-signed',
        'pendingMsgs'       : 'integer-hex-signed',
        'expungedBytes'     : 'integer-hex',
        'folderSize'        : 'integer-hex',
    },

    # Mail Summary File Fields
    # (ns:msg:db:row:scope:{dbfolderinfo,msgs,threads})
    'ns:msg:db:row:scope:dbfolderinfo:all' : {
        'current-view'         : 'current-view',
        # The next several are from
        # TB3.0.5:mailnews/db/msgdb/src/nsMsgDatabase.cpp
        # GetMsgRetentionSetting.
        'retainBy'             : 'retain-by',
        'daysToKeepHdrs'       : 'integer-hex',
        'numHdrsToKeep'        : 'integer-hex',
        'daysToKeepBodies'     : 'integer-hex',
        'keepUnreadOnly'       : 'boolean-integer',
        'useServerDefaults'    : 'boolean-integer',
        'cleanupBodies'        : 'boolean-integer',

        # The next several are shared with ns:msg:db:row:scope:folders:all
        'LastPurgeTime'        : 'last-purge-time',
        'MRUTime'              : 'seconds',
        'expungedBytes'        : 'integer-hex',
        'flags'                : 'message-folder-flags',
        'folderSize'           : 'integer-hex',

        # The next several are from
        # TB3.0.5:mailnews/db/msgdb/src/nsDBFolderInfo.cpp.
        'numMsgs'              : 'integer-hex',
        'numNewMsgs'           : 'integer-hex',
        'folderDate'           : 'seconds-hex',
        'charSetOverride'      : 'boolean-integer',
        'viewType'             : 'view-type',
        'viewFlags'            : 'view-flags',
        'sortType'             : 'sort-type',
        'sortOrder'            : 'sort-order',

        # From TB3.0.5:mailnews/db/msgdb/src/nsMsgDatabase.cpp.
        'fixedBadRefThreading' : 'boolean-integer',
        'imapFlags'            : 'imap-flags',
        'sortColumns'          : 'sort-columns',
    },
    'ns:msg:db:row:scope:msgs:all' : {
        'ProtoThreadFlags'    : 'message-flags',

        # The next several are defined in
        # TB3.0.5:mailnews/db/msgdb/src/nsMsgDatabase.cpp and are actually
        # used in mailnews/db/msgdb/src/nsMsgHdr.cpp.
        'date'                : 'seconds-hex',
        'size'                : 'integer-hex',
        'flags'               : 'message-flags',
        'priority'            : 'priority',
        'label'               : 'integer-hex',
        'statusOfset'         : 'integer-hex',
        'numLines'            : 'integer-hex',
        'msgOffset'           : 'integer-hex',
        'offlineMsgSize'      : 'integer-hex',
        # Same files, but Thunderbird 2.0.0.24.
        'numRefs'             : 'integer-hex',
        # From TB3.0.5:mailnews/local/src/nsParseMailbox.cpp.
        'dateReceived'        : 'seconds-hex',
        'remoteContentPolicy' : 'remote-content-policy',
    },

    # Mail Summary File meta-rows.
    'm' : {
        # These are all declared in
        # TB3.0.5:mailnews/db/msgdb/src/nsMsgDatabase.cpp and read in in
        # mailnews/db/msgdb/src/nsMsgThread.cpp InitCachedValues.
        'children'            : 'integer-hex',
        'unreadChildren'      : 'integer-hex',
        'threadFlags'         : 'message-flags',
        'threadNewestMsgDate' : 'seconds-hex',
    },
}

class FieldConverter(Filter):
    '''
    Filter to interpret Mork fields, making them more human-readable.
    '''
    def __init__(self, order):
        self.mork_filter_order = order

    def add_options(self, parser):
        group = optparse.OptionGroup(parser, 'Field Conversion Options')

        group.add_option('-x', '--no-convert', action='store_true',
            help="don't do any of the usual field conversions")
        group.add_option('--no-time', action='store_true',
            help="don't do time/date conversions")
        group.add_option('--time-format', metavar='FORMAT',
            help='use FORMAT as the strftime format for times/dates '
                 '(default: %c)')
        group.add_option('--no-base', action='store_true',
            help="don't convert hexidecimal integers to decimal")
        group.add_option('--no-symbolic', action='store_true',
            help="don't do symbolic conversions (e.g. flags, booleans, and "
                 "number-to-string conversions)")

        parser.add_option_group(group)
        parser.set_defaults(time_format='%c')

    def process(self, db, opts):
        if opts.no_convert:
            return

        field = converters.FieldInfo(opts, db)

        for (row_namespace, row_id, row) in db.rows.items():
            row_conversions = _conversions.get(row_namespace)
            if row_conversions is None:
                continue

            for (col, value) in row.items():
                conversion = row_conversions.get(col)
                converter = _converters.get(conversion)
                if converter:
                    field.set_value(row_namespace, col, value)
                    try:
                        row[col] = converter.convert(field)
                    except converters.ConversionError, e:
                        warnings.warn(
                            'unconvertible value, consider using '
                            '--convert option\n'
                            ' [value: %r; conversion: %s; message: %r;\n'
                            '  row namespace: %s; column: %s]' %
                                (value, conversion, str(e), row_namespace, col)
                        )

convert_fields = FieldConverter(4200)
