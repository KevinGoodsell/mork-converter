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
import re

class FieldInfo(object):
    '''Holds all the information a converter might need.'''

    def __init__(self, opts, db):
        self.opts = opts
        self.db = db

        # items to be set in set_value
        self.row_ns = None
        self.column = None
        self.value = None

    def set_value(self, row_ns, column, value):
        self.row_ns = row_ns
        self.column = column
        self.value = value

class ConversionError(ValueError):
    pass

# Converters for different field types:

class FieldConverter(object):
    description = None
    # To distinguish converters that may be generally useful from those that
    # the user will probably never want to use directly, they are marked as
    # generic or not generic, respectively.
    generic = False

    def convert(self, field):
        raise NotImplementedError();

class NullConverter(FieldConverter):
    description = 'No-op converter. Leaves the value unchanged.'
    generic = True

    def convert(self, field):
        return field.value

class Int(FieldConverter):
    base = 10

    def convert(self, field):
        if field.opts.no_base:
            return field.value

        return unicode(self._to_int(field.value))

    def _to_int(self, value):
        try:
            return int(value, self.base)
        except ValueError, e:
            raise ConversionError(str(e))

class IntHex(Int):
    description = 'Converts hexadecimal integer values to decimal.'
    generic = True
    base = 16

class SignedInt32(Int):
    description = 'Converts 32-bit hexadecimal integer values to (possibly '\
                  'negative) decimal values.'
    generic = True
    base = 16

    def convert(self, field):
        if field.opts.no_base:
            return field.value

        ival = self._to_int(field.value)
        if ival > 0xffffffff:
            raise ConversionError('integer too large for 32 bits')
        if ival > 0x7fffffff:
            ival -= 0x100000000

        return unicode(ival)

# From TB3.0.5:mailnews/imap/src/nsImapMailFolder.cpp, with constants in
# mailnews/imap/src/nsImapCore.h
class HierDelim(Int):
    description = "Converter for the 'hierDelim' column from folder cache "\
                  "files (panacea.dat)."
    base = 16

    def convert(self, field):
        if field.opts.no_symbolic:
            return field.value

        ival = self._to_int(field.value)
        try:
            cval = chr(ival)
        except ValueError, e:
            raise ConversionError(str(e))
        if cval == '^':
            return 'kOnlineHierarchySeparatorUnknown'
        elif cval == '|':
            return 'kOnlineHierarchySeparatorNil'
        else:
            return cval

class Flags(Int):
    base = 16
    flag_values = None
    empty = ''

    def convert(self, field):
        if field.opts.no_symbolic:
            return field.value

        ival = self._to_int(field.value)
        flags = self._get_flags(ival, field)
        if flags:
            return ' '.join(flags)
        else:
            return self.empty

    def _get_flags(self, ival, field):
        result = []
        for (i, flag) in enumerate(self.flag_values):
            if not flag:
                continue

            fval = 1 << i
            if fval & ival:
                result.append(flag)
                ival -= fval

        if ival:
            warnings.warn('unknown flags\n'
                          ' [value: 0x%x; row namespace: %s; column: %s]' %
                              (ival, field.row_ns, field.column),
                          stacklevel=2)

        return result

# TB3.0.5:mailnews/base/public/nsMsgMessageFlags.idl nsMsgMessageFlags
# Message "flags" include some non-flag parts.
class MsgFlags(Flags):
    description = 'Converter for message and thread flags.'

    flag_values = ['Read', 'Replied', 'Marked', 'Expunged', 'HasRe', 'Elided',
                   'FeedMsg', 'Offline', 'Watched', 'SenderAuthed', 'Partial',
                   'Queued', 'Forwarded', None, None, None, 'New', None,
                   'Ignored', None, None, 'IMAPDeleted', 'MDNReportNeeded',
                   'MDNReportSent', 'Template', None, None, None, 'Attachment']

    # TB3.0.5:mailnews/base/public/MailNewsTypes2.idl
    _priority_labels = ['notSet', 'none', 'lowest', 'low', 'normal', 'high',
                        'highest']

    def convert(self, field):
        if field.opts.no_symbolic:
            return field.value

        ival = self._to_int(field.value)
        # Deal with non-flags:
        # Priorities = 0xE000
        priorities = ival & 0xE000
        ival -= priorities
        priorities >>= 13
        if priorities >= len(self._priority_labels):
            raise ConversionError('invalid priority (%d)' % priorities)
        # Labels = 0xE000000
        labels = ival & 0xE000000
        ival -= labels
        labels >>= 25

        flags = self._get_flags(ival, field)

        if priorities:
            # Note that there's actually just one priority, but the name
            # 'Priorities' is used in the flag definitions.
            flags.append('Priorities:%s' % self._priority_labels[priorities])
        if labels:
            flags.append('Labels:0x%X' % labels)

        return ' '.join(flags)

# From TB3.0.5:mailnews/imap/src/nsImapMailFolder.cpp.
# Flags are in mailnews/imap/src/nsImapCore.h.
class ImapFlags(Flags):
    description = 'Converter for IMAP folder flags.'

    flag_values = ['kImapMsgSeenFlag', 'kImapMsgAnsweredFlag',
                   'kImapMsgFlaggedFlag', 'kImapMsgDeletedFlag',
                   'kImapMsgDraftFlag', 'kImapMsgRecentFlag',
                   'kImapMsgForwardedFlag', 'kImapMsgMDNSentFlag',
                   'kImapMsgCustomKeywordFlag', None, None, None, None,
                   'kImapMsgSupportMDNSentFlag',
                   'kImapMsgSupportForwardedFlag', 'kImapMsgSupportUserFlag']
    empty = 'kNoImapMsgFlag'

    def convert(self, field):
        if field.opts.no_symbolic:
            return field.value

        ival = self._to_int(field.value)
        # Handle labels
        labels = ival & 0xE00
        ival -= labels
        labels >>= 9

        flags = self._get_flags(ival, field)

        if labels:
            flags.append('Labels:0x%X' % labels)

        return ' '.join(flags)

# TB3.0.5:mailnews/base/util/nsMsgDBFolder.cpp with flags defined in
# mailnews/base/public/nsMsgFolderFlags.idl
class MsgFolderFlags(Flags):
    description = 'Converts message folder flags.'

    flag_values = ['Newsgroup', 'NewsHost', 'Mail', 'Directory', 'Elided',
                   'Virtual', 'Subscribed', 'Unused2', 'Trash', 'SentMail',
                   'Drafts', 'Queue', 'Inbox', 'ImapBox', 'Archive',
                   'ProfileGroup', 'Unused4', 'GotNew', 'ImapServer',
                   'ImapPersonal', 'ImapPublic', 'ImapOtherUser', 'Templates',
                   'PersonalShared', 'ImapNoselect', 'CreatedOffline',
                   'ImapNoinferiors', 'Offline', 'OfflineEvents', 'CheckNew',
                   'Junk', 'Favorite']

# This shows up in TB3.0.5:mailnews/imap/src/nsImapMailFolder.cpp.
# Flag values are defined in mailnews/imap/src/nsImapMailFolder.h.
class AclFlags(Flags):
    description = 'Decodes IMAP Access Control List flags.'

    flag_values = ['IMAP_ACL_READ_FLAG', 'IMAP_ACL_STORE_SEEN_FLAG',
                   'IMAP_ACL_WRITE_FLAG', 'IMAP_ACL_INSERT_FLAG',
                   'IMAP_ACL_POST_FLAG', 'IMAP_ACL_CREATE_SUBFOLDER_FLAG',
                   'IMAP_ACL_DELETE_FLAG', 'IMAP_ACL_ADMINISTER_FLAG',
                   'IMAP_ACL_RETRIEVED_FLAG', 'IMAP_ACL_EXPUNGE_FLAG',
                   'IMAP_ACL_DELETE_FOLDER']

# From TB3.0.5:mailnews/imap/src/nsImapMailFolder.cpp. Flags defined in
# mailnews/imap/src/nsImapCore.h.
class BoxFlags(Flags):
    description = 'Decodes flags for IMAP mailboxes.'

    flag_values = ['kMarked', 'kUnmarked', 'kNoinferiors', 'kNoselect',
                   'kImapTrash', 'kJustExpunged', 'kPersonalMailbox',
                   'kPublicMailbox', 'kOtherUsersMailbox', 'kNameSpace',
                   'kNewlyCreatedFolder', 'kImapDrafts', 'kImapSpam',
                   'kImapSent', 'kImapInbox', 'kImapAllMail',
                   'kImapXListTrash']
    empty = 'kNoFlags'

# Flag from TB3.0.5:mailnews/base/public/nsIMsgDBView.idl.
class ViewFlags(Flags):
    description = 'Converts flags for folder views.'

    flag_values = ['kThreadedDisplay', None, None, 'kShowIgnored',
                   'kUnreadOnly', 'kExpandAll', 'kGroupBySort']
    empty = 'kNone'

class Enumeration(Int):
    base = 16
    values = None
    default = None

    def __init__(self):
        Int.__init__(self)

        if isinstance(self.values, dict):
            self._map = dict(self.values)
        else:
            self._map = dict(enumerate(self.values))

    def convert(self, field):
        if field.opts.no_symbolic:
            return field.value

        if field.value == '':
            result = self.default
        else:
            ival = self._to_int(field.value)
            result = self._map.get(ival, self.default)

        if result is None:
            # No conversion
            return field.value
        else:
            return result

# Based on TB2.0.0.24:mailnews/addrbook/src/nsAddrDatabase.h AddCardType,
# CardType appears to be a string. However, based on calls to
# GetCardTypeFromString in mailnews/addrbook/src/nsAbCardProperty.cpp, and the
# definition of constants in mailnews/addrbook/public/nsIAbCard.idl, it appears
# to be an enumeration with a bizarre string-formatted integer internal
# representation.
class CardType(Enumeration):
    description = 'Converter for address book entry type.'
    values = ['normal', 'AOL groups', 'AOL additional email']
    default = 'normal'

# current-view seems to have duplicate definitions in
# TB3.0.5:suite/mailnews/msgViewPickerOverlay.js and
# mail/base/modules/mailViewManager.js.
class CurrentView(Enumeration):
    description = 'Converts current folder view.'
    values = ['kViewItemAll', 'kViewItemUnread', 'kViewItemTags',
              'kViewItemNotDeleted', None, None, None, 'kViewItemVirtual',
              'kViewItemCustomize', 'kViewItemFirstCustom']

# TB3.0.5:mailnews/addrbook/src/nsAbCardProperty.cpp ConvertToEscapedVCard
# with constants in mailnews/addrbook/public/nsIAbCard.idl
class PreferMailFormat(Enumeration):
    description = 'Converts preferred mail format.'
    values = ['unknown', 'plaintext', 'html']

# TB3.0.5:mailnews/db/msgdb/src/nsMsgDatabase.cpp GetMsgRetentionSetting and
# ApplyRetentionSettings with values from
# mailnews/db/msgdb/public/nsIMsgDatabase.idl.
class RetainBy(Enumeration):
    description = 'Converts mail retention policy.'
    values = [None, 'nsMsgRetainAll', 'nsMsgRetainByAge',
              'nsMsgRetainByNumHeaders']

# TB3.0.5:mailnews/db/msgdb/src/nsDBFolderInfo.cpp with values from
# mailnews/base/public/nsIMsgDBView.idl.
class ViewType(Enumeration):
    description = 'Converts type of folder view.'
    values = ['eShowAllThreads', None, 'eShowThreadsWithUnread',
              'eShowWatchedThreadsWithUnread', 'eShowQuickSearchResults',
              'eShowVirtualFolderResults', 'eShowSearch']

# TB3.0.5:mailnews/db/msgdb/src/nsDBFolderInfo.cpp with values from
# mailnews/base/public/nsIMsgDBView.idl.
class SortType(Enumeration):
    description = 'Converts folder sort type.'
    values = {0x11 : 'byNone', 0x12 : 'byDate', 0x13 : 'bySubject',
              0x14 : 'byAuthor', 0x15 : 'byId', 0x16 : 'byThread',
              0x17 : 'byPriority', 0x18 : 'byStatus', 0x19 : 'bySize',
              0x1a : 'byFlagged', 0x1b : 'byUnread', 0x1c : 'byRecipient',
              0x1d : 'byLocation', 0x1e : 'byTags', 0x1f : 'byJunkStatus',
              0x20 : 'byAttachments', 0x21 : 'byAccount', 0x22 : 'byCustom',
              0x23 : 'byReceived'}

# TB3.0.5:mailnews/db/msgdb/src/nsDBFolderInfo.cpp with values from
# mailnews/base/public/nsIMsgDBView.idl.
class SortOrder(Enumeration):
    description = 'Converts folder sort order.'
    values = ['none', 'ascending', 'descending']

# Used in TB3.0.5:mailnews/db/msgdb/src/nsMsgHdr.cpp with constants from
# mailnews/base/public/MailNewsTypes2.idl.
class Priority(Enumeration):
    description = 'Converts message priority.'
    values = ['notSet', 'none', 'lowest', 'low', 'normal', 'high', 'highest']

# From TB3.0.5:mailnews/base/src/nsMsgContentPolicy.cpp.
class RemoteContentPolicy(Enumeration):
    description = 'Converts message remote content policy.'
    values = ['kNoRemoteContentPolicy', 'kBlockRemoteContent',
              'kAllowRemoteContent']

class BoolInt(Enumeration):
    description = 'Converter for boolean values represented as 0 or 1.'
    generic = True
    values = ['false', 'true']

# This is for fields that signal something by their mere presence. The value
# doesn't matter.
class BoolAnyVal(FieldConverter):
    description = "Converts any value to 'true', for boolean values "\
                  "indicated by their presence or absence."
    generic = True

    def convert(self, field):
        if field.opts.no_symbolic:
            return field.value

        return 'true'

class Time(FieldConverter):
    def _format(self, opts, t):
        return time.strftime(opts.time_format, t)

    def _to_time(self, field):
        raise NotImplementedError()

    def convert(self, field):
        if field.opts.no_time:
            return field.value

        t = self._to_time(field)
        return self._format(field.opts, t)

class Seconds(Time):
    description = 'Converts seconds since epoch to formatted time.'
    generic = True
    base = 10
    divisor = 1

    def convert(self, field):
        # 0 is a common value, and obviously doesn't represent a valid time.
        if field.value == '0':
            return field.value

        return Time.convert(self, field)

    def _to_time(self, field):
        try:
            as_int = int(field.value, self.base)
            seconds = as_int / self.divisor
            return time.localtime(seconds)
        # This should catch errors from int() and localtime()
        except ValueError, e:
            raise ConversionError(str(e))


class FormattedTime(Time):
    # Define this in derived classes
    parse_format = None

    def _to_time(self, field):
        try:
            return time.strptime(field.value, self.parse_format)
        except ValueError, e:
            raise ConversionError(str(e))

class SecondsHex(Seconds):
    description = 'Converts hexadecimal seconds since epoch to formatted time.'
    base = 16

class Microseconds(Seconds):
    description = 'Converts microseconds since epoch to formatted time.'
    divisor = 1000000

class SecondsGuessBase(Seconds):
    description = 'Convert number of seconds to formatted time, attempting '\
                  'to guess the number base.'

    _known_bases = {} # {('row_ns', 'column') : int(base)}
    _hex_matcher = re.compile(r'[a-f]+', re.IGNORECASE)

    def _to_time(self, field):
        base = self._known_bases.get((field.row_ns, field.column))
        if base is None:
            base = self._search_for_base(field)
            self._known_bases[(field.row_ns, field.column)] = base

        try:
            seconds = int(field.value, base)
            return time.localtime(seconds)
        # This should catch errors from int() and localtime()
        except ValueError, e:
            raise ConversionError(str(e))

    def _search_for_base(self, field):
        for (row_ns, row_id, row) in field.db.rows.items():
            val = row.get(field.column)
            if val and self._hex_matcher.search(val):
                base = 16
                break
        else:
            try:
                as_dec = int(field.value)
            except ValueError, e:
                raise ConversionError(str(e))

            warnings.warn("uncertain number base; consider using --convert "
                          "with 'seconds' or 'seconds-hex'\n"
                          " [value: %r; row namespace: %s; column: %s]" %
                          (field.value, field.row_ns, field.column))

            # 80000000_10 = Fri Jul 14 22:13:20 1972
            # 80000000_16 = Tue Jan 19 03:14:08 2038
            #   (but likely out of the system's time_t range)
            # With this the result may be wrong when:
            # - the value is hex and later than Jan 19 2038
            # - the value is decimal and earlier than Jul 1972
            if as_dec >= 80000000:
                base = 10
            else:
                base = 16

        return base

# TB3.0.5:mailnews/db/msgdb/src/nsMsgDatabase.cpp.
class LastPurgeTime(FormattedTime):
    description = "Converter for LastPurgeTime's formatted date/time."
    parse_format = '%a %b %d %H:%M:%S %Y'

# From TB3.0.5:mailnews/base/src/nsMsgDBView.cpp, using constants from
# mailnews/base/public/nsIMsgDBView.idl. DecodeColumnSort describes how
# to handle this.
class SortColumns(FieldConverter):
    description = 'Converter for mail folder sort column.'

    _sort_order = {
        '0' : 'none',
        '1' : 'ascending',
        '2' : 'descending',
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

    def convert(self, field):
        if field.opts.no_symbolic:
            return field.value

        sort_items = []

        # Normally, the value should be a sequence of byte-pairs, where the
        # first is a sort-type value and the second is a sort-order value.
        # These two values are represented differently, with the sort-type
        # using the raw byte value and the sort-order being an ASCII digit.
        #
        # The more complicated case is when sort-type is byCustom. In this case
        # the name of the custom column appears as a carriage-return-terminated
        # string following the sort-order digit.

        for piece in field.value.split('\r'):
            it = iter(piece)
            for isort_type in it:
                try:
                    isort_order = next(it)
                except StopIteration:
                    raise ConversionError('incorrect field format')

                sort_type = self._sort_type.get(ord(isort_type))
                sort_order = self._sort_order.get(isort_order)

                if sort_type is None or sort_order is None:
                    raise ConversionError('out of range field value')

                sort_item = 'type:%s order:%s' % (sort_type, sort_order)

                if sort_type == 'byCustom':
                    # The rest is the custom column name (or something like
                    # that).
                    custom_col = ''.join(it)
                    sort_item = '%s custom:%s' % (sort_item, custom_col)

                sort_items.append(sort_item)

        return ', '.join(sort_items)
