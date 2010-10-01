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
import time
import optparse

from filterbase import Filter

# Converters for different field types:

class _FieldConverter(object):
    description = None
    # To distinguish converters that may be generally useful from those that
    # the user will probably never want to use directly, they are marked as
    # generic or not generic, respectively.
    generic = False

    def convert(self, opts, value):
        raise NotImplementedError();

class _NullConverter(_FieldConverter):
    description = 'No-op converter. Leaves the value unchanged.'
    generic = True

    def convert(self, opts, value):
        return value

class _Int(_FieldConverter):
    def __init__(self, base):
        self._base = base

    def convert(self, opts, value):
        if opts.no_base:
            return value

        return unicode(self._to_int(value))

    def _to_int(self, value):
        return int(value, self._base)

class _IntHex(_Int):
    description = 'Converts hexadecimal integer values to decimal.'
    generic = True

    def __init__(self):
        _Int.__init__(self, 16)

class _SignedInt32(_Int):
    description = ('Converts 32-bit hexadecimal integer values to (possibly '
                   'negative) decimal values.')
    generic = True

    def __init__(self):
        _Int.__init__(self, 16)

    def convert(self, opts, value):
        if opts.no_base:
            return value

        ival = self._to_int(value)
        assert ival <= 0xffffffff, 'integer too large for 32 bits'
        if ival > 0x7fffffff:
            ival -= 0x100000000

        return unicode(ival)

class _HierDelim(_Int):
    description = ("Converter for the 'hierDelim' column from folder cache "
                   "files (panacea.dat).")

    def __init__(self):
        _Int.__init__(self, 16)

    def convert(self, opts, value):
        if opts.no_symbolic:
            return value

        ival = self._to_int(value)
        cval = unichr(ival)
        if cval == u'^':
            return u'kOnlineHierarchySeparatorUnknown'
        elif cval == u'|':
            return u'kOnlineHierarchySeparatorNil'
        else:
            return cval

class _Flags(_Int):
    def __init__(self, values, empty=u'', base=16):
        _Int.__init__(self, base)

        self._empty = empty
        self._values = list(values)

    def convert(self, opts, value):
        if opts.no_symbolic:
            return value

        ival = self._to_int(value)
        flags = self._get_flags(opts, ival)
        if flags:
            return u' '.join(flags)
        else:
            return self._empty

    def _get_flags(self, opts, ival):
        result = []
        for (i, flag) in enumerate(self._values):
            if not flag:
                continue

            fval = 1 << i
            if fval & ival:
                result.append(flag)
                ival -= fval

        if ival:
            warnings.warn('unknown flags: %x' % ival)

        return result

# mailnews/base/public/nsMsgMessageFlags.idl nsMsgMessageFlags
# Message "flags" include some non-flag parts.
class _MsgFlags(_Flags):
    description = 'Converter for message and thread flags.'

    _flag_vals = [u'Read', u'Replied', u'Marked', u'Expunged', u'HasRe',
                  u'Elided', None, u'Offline', u'Watched', u'SenderAuthed',
                  u'Partial', u'Queued', u'Forwarded', None, None, None,
                  u'New', None, u'Ignored', None, None, u'IMAPDeleted',
                  u'MDNReportNeeded', u'MDNReportSent', u'Template',
                  None, None, None, u'Attachment']

    # mailnews/base/public/MailNewsTypes2.idl
    _priority_labels = ['notSet', 'none', 'lowest', 'low', 'normal', 'high',
                        'highest']

    def __init__(self):
        _Flags.__init__(self, self._flag_vals)

    def convert(self, opts, value):
        if opts.no_symbolic:
            return value

        ival = self._to_int(value)
        # Deal with non-flags:
        # Priorities = 0xE000
        priorities = ival & 0xE000
        ival -= priorities
        priorities >>= 13
        assert priorities < len(self._priority_labels), 'invalid priority'
        # Labels = 0xE000000
        labels = ival & 0xE000000
        ival -= labels
        labels >>= 25

        flags = self._get_flags(opts, ival)

        if priorities:
            flags.append('Priorities:%s' % self._priority_labels[priorities])
        if labels:
            flags.append('Labels:0x%X' % labels)

        return u' '.join(flags)

class _ImapFlags(_Flags):
    description = 'Converter for IMAP folder flags.'

    _flag_vals = ['kImapMsgSeenFlag', 'kImapMsgAnsweredFlag',
                  'kImapMsgFlaggedFlag', 'kImapMsgDeletedFlag',
                  'kImapMsgDraftFlag', 'kImapMsgRecentFlag',
                  'kImapMsgForwardedFlag', 'kImapMsgMDNSentFlag',
                  'kImapMsgCustomKeywordFlag', None, None, None, None,
                  'kImapMsgSupportMDNSentFlag', 'kImapMsgSupportForwardedFlag',
                  'kImapMsgSupportUserFlag']

    def __init__(self):
        _Flags.__init__(self, self._flag_vals, 'kNoImapMsgFlag')

    def convert(self, opts, value):
        if opts.no_symbolic:
            return value

        ival = self._to_int(value)
        # Handle labels
        labels = ival & 0xE00
        ival -= labels
        labels >>= 9

        flags = self._get_flags(opts, ival)

        if labels:
            flags.append('Labels:0x%X' % labels)

        return u' '.join(flags)

class _MsgFolderFlags(_Flags):
    description = 'Converts message folder flags.'

    def __init__(self):
        # mailnews/base/public/nsMsgFolderFlags.idl
        _Flags.__init__(self, ['Newsgroup', 'NewsHost', 'Mail', 'Directory',
                               'Elided', 'Virtual', 'Subscribed', 'Unused2',
                               'Trash', 'SentMail', 'Drafts', 'Queue', 'Inbox',
                               'ImapBox', 'Archive', 'ProfileGroup', 'Unused4',
                               'GotNew', 'ImapServer', 'ImapPersonal',
                               'ImapPublic', 'ImapOtherUser', 'Templates',
                               'PersonalShared', 'ImapNoselect',
                               'CreatedOffline', 'ImapNoinferiors', 'Offline',
                               'OfflineEvents', 'CheckNew', 'Junk',
                               'Favorite'])

class _AclFlags(_Flags):
    description = 'Decodes IMAP Access Control List flags.'

    _flag_vals = ['IMAP_ACL_READ_FLAG', 'IMAP_ACL_STORE_SEEN_FLAG',
                  'IMAP_ACL_WRITE_FLAG', 'IMAP_ACL_INSERT_FLAG',
                  'IMAP_ACL_POST_FLAG', 'IMAP_ACL_CREATE_SUBFOLDER_FLAG',
                  'IMAP_ACL_DELETE_FLAG', 'IMAP_ACL_ADMINISTER_FLAG',
                  'IMAP_ACL_RETRIEVED_FLAG', 'IMAP_ACL_EXPUNGE_FLAG',
                  'IMAP_ACL_DELETE_FOLDER']

    def __init__(self):
        _Flags.__init__(self, self._flag_vals)

class _BoxFlags(_Flags):
    description = 'Decodes flags for IMAP mailboxes.'

    _flag_vals = ['kMarked', 'kUnmarked', 'kNoinferiors', 'kNoselect',
                  'kImapTrash', 'kJustExpunged', 'kPersonalMailbox',
                  'kPublicMailbox', 'kOtherUsersMailbox', 'kNameSpace',
                  'kNewlyCreatedFolder', 'kImapDrafts', 'kImapSpam',
                  'kImapSent', 'kImapInbox', 'kImapAllMail', 'kImapXListTrash']

    def __init__(self):
        _Flags.__init__(self, self._flag_vals, 'kNoFlags')

class _ViewFlags(_Flags):
    description = 'Converts flags for folder views.'

    _flag_vals = ['kThreadedDisplay', None, None, 'kShowIgnored',
                  'kUnreadOnly', 'kExpandAll', 'kGroupBySort']

    def __init__(self):
        _Flags.__init__(self, self._flag_vals, 'kNone')

class _Enumeration(_Int):
    def __init__(self, values, default=None, base=16):
        _Int.__init__(self, base)

        if isinstance(values, dict):
            self._map = dict(values)
        else:
            self._map = dict(enumerate(values))

        self._default = default

    def convert(self, opts, value):
        if opts.no_symbolic:
            return value

        if value == '':
            result = self._default
        else:
            ival = self._to_int(value)
            result = self._map.get(ival, self._default)

        if result is None:
            # No conversion
            return value
        else:
            return result

class _CardType(_Enumeration):
    description = 'Converter for address book entry type.'

    def __init__(self):
        _Enumeration.__init__(self, [u'normal', u'AOL groups',
                                     u'AOL additional email'],
                              default=u'normal')

class _CurrentView(_Enumeration):
    description = 'Converts current folder view.'

    def __init__(self):
        _Enumeration.__init__(self, [u'kViewItemAll', u'kViewItemUnread',
                                     u'kViewItemTags', u'kViewItemNotDeleted',
                                     None, None, None, u'kViewItemVirtual',
                                     u'kViewItemCustomize',
                                     u'kViewItemFirstCustom'])

class _PreferMailFormat(_Enumeration):
    description = 'Converts preferred mail format.'

    def __init__(self):
        _Enumeration.__init__(self, [u'unknown', u'plaintext', u'html'])

class _RetainBy(_Enumeration):
    description = 'Converts mail retention policy.'

    def __init__(self):
        _Enumeration.__init__(self, [None, 'nsMsgRetainAll',
                                     'nsMsgRetainByAge',
                                     'nsMsgRetainByNumHeaders'])

class _ViewType(_Enumeration):
    description = 'Converts type of folder view.'

    def __init__(self):
        _Enumeration.__init__(self, ['eShowAllThreads', None,
                                     'eShowThreadsWithUnread',
                                     'eShowWatchedThreadsWithUnread',
                                     'eShowQuickSearchResults',
                                     'eShowVirtualFolderResults',
                                     'eShowSearch'])

class _SortType(_Enumeration):
    description = 'Converts folder sort type.'

    def __init__(self):
        _Enumeration.__init__(self, {0x11 : 'byNone',
                                     0x12 : 'byDate',
                                     0x13 : 'bySubject',
                                     0x14 : 'byAuthor',
                                     0x15 : 'byId',
                                     0x16 : 'byThread',
                                     0x17 : 'byPriority',
                                     0x18 : 'byStatus',
                                     0x19 : 'bySize',
                                     0x1a : 'byFlagged',
                                     0x1b : 'byUnread',
                                     0x1c : 'byRecipient',
                                     0x1d : 'byLocation',
                                     0x1e : 'byTags',
                                     0x1f : 'byJunkStatus',
                                     0x20 : 'byAttachments',
                                     0x21 : 'byAccount',
                                     0x22 : 'byCustom',
                                     0x23 : 'byReceived'})

class _SortOrder(_Enumeration):
    description = 'Converts folder sort order.'

    def __init__(self):
        _Enumeration.__init__(self, ['none', 'ascending', 'descending'])

class _Priority(_Enumeration):
    description = 'Converts message priority.'

    def __init__(self):
        _Enumeration.__init__(self, ['notSet', 'none', 'lowest', 'low',
                                     'normal', 'high', 'highest'])

class _RemoteContentPolicy(_Enumeration):
    description = 'Converts message remote content policy.'

    def __init__(self):
        _Enumeration.__init__(self, ['kNoRemoteContentPolicy',
                                     'kBlockRemoteContent',
                                     'kAllowRemoteContent'])

class _BoolInt(_Enumeration):
    description = 'Converter for boolean values represented as 0 or 1.'
    generic = True

    def __init__(self):
        _Enumeration.__init__(self, [u'false', u'true'])

# This is for fields that signal something by their mere presence. The value
# doesn't matter.
class _BoolAnyVal(_FieldConverter):
    description = ("Converts any value to 'true', for boolean values "
                   "indicated by their presence or absence.")
    generic = True

    def convert(self, opts, value):
        if opts.no_symbolic:
            return value

        return u'true'

class _Time(_FieldConverter):
    def _format(self, opts, t):
        return time.strftime(opts.time_format, t)

class _Seconds(_Time):
    description = 'Converts seconds since epoch to formatted time.'
    generic = True

    def __init__(self, base=10, divisor=1):
        self._base = base
        self._divisor = divisor

    def convert(self, opts, value):
        if opts.no_time:
            return value

        # 0 is a common value, and obviously doesn't represent a valid time.
        if value == '0':
            return value

        seconds = int(value, self._base) / self._divisor
        t = time.localtime(seconds)

        return self._format(opts, t)

class _FormattedTime(_Time):
    def __init__(self, parse_format):
        self._parse_format = parse_format

    def convert(self, opts, value):
        if opts.no_time:
            return value

        t = time.strptime(value, self._parse_format)
        return self._format(opts, t)

class _SecondsHex(_Seconds):
    description = 'Converts hexidecimal seconds since epoch to formatted time.'

    def __init__(self):
        _Seconds.__init__(self, base=16)

class _Microseconds(_Seconds):
    description = 'Converts microseconds since epoch to formatted time.'

    def __init__(self):
        _Seconds.__init__(self, divisor=1000000)

class _LastPurgeTime(_FormattedTime):
    description = "Converter for LastPurgeTime's formatted date/time."

    def __init__(self):
        _FormattedTime.__init__(self, '%a %b %d %H:%M:%S %Y')

class _SortColumns(_FieldConverter):
    description = 'Converter for mail folder sort column.'

    # constants from mailnews/base/public/nsIMsgDBView.idl.
    _sort_order = {
        0 : 'none',
        1 : 'ascending',
        2 : 'descending',
    }

    _sort_type = {
        0x11 : 'byNone',
        0x12 : 'byDate',
        0x13 : 'bySubject',
        0x14 : 'byAuthor',
        0x15 : 'byId',
        0x16 : 'byThread',
        0x17 : 'byPriority',
        0x18 : 'byStatus',
        0x19 : 'bySize',
        0x1a : 'byFlagged',
        0x1b : 'byUnread',
        0x1c : 'byRecipient',
        0x1d : 'byLocation',
        0x1e : 'byTags',
        0x1f : 'byJunkStatus',
        0x20 : 'byAttachments',
        0x21 : 'byAccount',
        0x22 : 'byCustom',
        0x23 : 'byReceived',
    }

    def convert(self, opts, value):
        if opts.no_symbolic:
            return value

        sort_items = []

        for piece in value.split('\r'):
            it = iter(piece)
            for isort_type in it:
                isort_order = ord(next(it)) - ord('0')

                sort_type = self._sort_type.get(ord(isort_type))
                sort_order = self._sort_order.get(isort_order)

                assert sort_type is not None, 'invalid sort type'
                assert sort_order is not None, 'invalid sort order'

                sort_item = u'type:%s order:%s' % (sort_type, sort_order)

                if sort_type == 'byCustom':
                    # The rest is the custom column name (or something like
                    # that).
                    custom_col = str(it)
                    sort_item = '%s custom:%s' % (sort_item, custom_col)

                sort_items.append(sort_item)

        return u', '.join(sort_items)

_converters = {
    # General converters first.
    'none'               : _NullConverter(),
    'integer-hex'        : _IntHex(),
    'integer-hex-signed' : _SignedInt32(),
    'boolean-integer'    : _BoolInt(),
    'boolean-any'        : _BoolAnyVal(),
    'seconds'            : _Seconds(),
    'seconds-hex'        : _SecondsHex(),
    'microseconds'       : _Microseconds(),

    # Specific converters second.
    'hier-delim'            : _HierDelim(),
    'message-flags'         : _MsgFlags(),
    'imap-flags'            : _ImapFlags(),
    'sort-columns'          : _SortColumns(),
    'last-purge-time'       : _LastPurgeTime(),
    'message-folder-flags'  : _MsgFolderFlags(),
    'card-type'             : _CardType(),
    'prefer-mail-format'    : _PreferMailFormat(),
    'acl-flags'             : _AclFlags(),
    'box-flags'             : _BoxFlags(),
    'current-view'          : _CurrentView(),
    'retain-by'             : _RetainBy(),
    'view-type'             : _ViewType(),
    'view-flags'            : _ViewFlags(),
    'sort-type'             : _SortType(),
    'sort-order'            : _SortOrder(),
    'priority'              : _Priority(),
    'remote-content-policy' : _RemoteContentPolicy(),
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
