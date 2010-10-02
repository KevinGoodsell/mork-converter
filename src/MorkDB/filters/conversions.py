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

# XXX The source references are kind of screwy now that the code is in the
# classes, not the dict.

# The big dictionary of field converters.
#
# Note: ns:addrbk, ns:history, ns:formhistory are pretty obvious, but ns:msg
# is used for both Mail Summary Files and Folder Caches. However, Folder Caches
# have :scope:folders and Mail Summary Files have several scopes, none of which
# are 'folders'.

_conversions = {
    # Address Book Fields (ns:addrbk).
    # Source references are for Thunderbird 3.0.5 unless otherwise
    # indicated.
    'ns:addrbk:db:row:scope:card:all' : {
        # mailnews/addrbook/src/nsAddrDatabase.h AddAllowRemoteContent
        'AllowRemoteContent' : 'boolean-integer',
        # Based on mailnews/addrbook/src/nsAddrDatabase.h AddCardType from
        # Thunderbird 2.0.0.24, CardType appears to be a string. However,
        # based on calls to GetCardTypeFromString in
        # mailnews/addrbook/src/nsAbCardProperty.cpp, and the definition of
        # constants in mailnews/addrbook/public/nsIAbCard.idl, it appears to be
        # an enumeration with a bizarre string-formatted integer internal
        # representation.
        'CardType'           : 'card-type',
        # mailnews/addrbook/src/nsAddrDatabase.cpp AddRowToDeletedCardsTable
        'LastModifiedDate'   : 'seconds-hex',
        # mailnews/addrbook/src/nsAddrDatabase.h AddPopularityIndex
        'PopularityIndex'    : 'integer-hex',
        # mailnews/addrbook/src/nsAbCardProperty.cpp ConvertToEscapedVCard
        'PreferMailFormat'   : 'prefer-mail-format',
    },
    'ns:addrbk:db:row:scope:list:all' : {
        # mailnews/addrbook/src/nsAddrDatabase.cpp GetListAddressTotal
        'ListTotalAddresses' : 'integer-hex',
    },

    # History Fields (ns:history).
    # Source references are from Firefox 2.0.0.20 unless otherwise indicated.
    'ns:history:db:row:scope:history:all' : {
        # Tokens are created in
        # /toolkit/components/history/src/nsGlobalHistory.cpp CreateTokens.
        # AddNewPageToDatabase in the same file is a good reference for these.

        'FirstVisitDate' : 'microseconds',
        'LastVisitDate'  : 'microseconds',
        'Hidden'         : 'boolean-any',
        'Typed'          : 'boolean-any',
    },

    # Folder Cache Fields (ns:msg:db:row:scope:folders:).
    # Source references are from Thunderbird 3.0.5 unless otherwise indicated.
    # Folder caches seem to share a lot of attributes with
    # ns:msg:db:row:scope:dbfolderinfo from .msf files.
    'ns:msg:db:row:scope:folders:all' : {
        # From mailnews/db/msgdb/src/nsMsgDatabase.cpp
        'LastPurgeTime'     : 'last-purge-time',
        # Defined in mailnews/base/public/msgCore.h, used
        # in mailnews/base/util/nsMsgDBFolder.cpp
        'MRUTime'           : 'seconds',
        # This shows up in mailnews/imap/src/nsImapMailFolder.cpp.
        # Flag values are defined in mailnews/imap/src/nsImapMailFolder.h.
        'aclFlags'          : 'acl-flags',
        # From mailnews/imap/src/nsImapMailFolder.cpp. Flags defined in
        # mailnews/imap/src/nsImapCore.h.
        'boxFlags'          : 'box-flags',
        # From mailnews/imap/src/nsImapMailFolder.cpp, with constants in
        # mailnews/imap/src/nsImapCore.h
        'hierDelim'         : 'hier-delim',

        # The remaining items are all from mailnews/base/util/nsMsgDBFolder.cpp

        # Flags are found in mailnews/base/public/nsMsgFolderFlags.idl.
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
    # Source references are for Thunderbird 3.0.5 unless otherwise indicated.
    'ns:msg:db:row:scope:dbfolderinfo:all' : {
        # current-view seems to have duplicate definitions in
        # suite/mailnews/msgViewPickerOverlay.js and
        # mail/base/modules/mailViewManager.js.
        'current-view'         : 'current-view',
        # The next several are from mailnews/db/msgdb/src/nsMsgDatabase.cpp
        # GetMsgRetentionSetting.
        # retainBy enum comes from mailnews/db/msgdb/public/nsIMsgDatabase.idl.
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

        # The next several are from mailnews/db/msgdb/src/nsDBFolderInfo.cpp.
        'numMsgs'              : 'integer-hex',
        'numNewMsgs'           : 'integer-hex',
        'folderDate'           : 'seconds-hex',
        'charSetOverride'      : 'boolean-integer',
        # Enum and flag values are in mailnews/base/public/nsIMsgDBView.idl
        'viewType'             : 'view-type',
        'viewFlags'            : 'view-flags',
        'sortType'             : 'sort-type',
        'sortOrder'            : 'sort-order',

        # From mailnews/db/msgdb/src/nsMsgDatabase.cpp.
        'fixedBadRefThreading' : 'boolean-integer',

        # From mailnews/imap/src/nsImapMailFolder.cpp.
        # Flags are in mailnews/imap/src/nsImapCore.h.
        'imapFlags'            : 'imap-flags',
        # From mailnews/base/src/nsMsgDBView.cpp, using consants from
        # mailnews/base/public/nsIMsgDBView.idl. DecodeColumnSort describes how
        # to handle this.
        'sortColumns'          : 'sort-columns',
    },
    'ns:msg:db:row:scope:msgs:all' : {
        # mailnews/imap/src/nsImapMailFolder.cpp
        'ProtoThreadFlags'    : 'message-flags',

        # The next several are defined in
        # mailnews/db/msgdb/src/nsMsgDatabase.cpp and are actually used in
        # mailnews/db/msgdb/src/nsMsgHdr.cpp.
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

        # From mailnews/local/src/nsParseMailbox.cpp
        'dateReceived'        : 'seconds-hex',
        # From mailnews/base/src/nsMsgContentPolicy.cpp
        'remoteContentPolicy' : 'remote-content-policy',
    },

    # Mail Summary File meta-rows.
    'm' : {
        # These are all declared in mailnews/db/msgdb/src/nsMsgDatabase.cpp
        # and read in in mailnews/db/msgdb/src/nsMsgThread.cpp
        # InitCachedValues.
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

        for (row_namespace, row_id, row) in db.rows.items():
            row_conversions = _conversions.get(row_namespace)
            if row_conversions is None:
                continue

            for (col, value) in row.items():
                conversion = row_conversions.get(col)
                converter = _converters.get(conversion)
                if converter:
                    row[col] = converter.convert(opts, value)

convert_fields = FieldConverter(4200)
