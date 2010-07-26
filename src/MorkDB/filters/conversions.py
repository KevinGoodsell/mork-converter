# XXX This entire thing is on hold while I look at simplifying. Probably want
# to take a more selective approach, esp. with .msf file fields.
import warnings
import time

from filterbase import Filter

# Converters for different field types:
# XXX I think maybe this should be generalized away from "converters" to "field
# types". Also, some of the inheritance is wrong.

class _FieldConverter(object):
    def convert(self, opts, value):
        raise NotImplementedError();

# A bunch of things don't really need converting (or I don't know how to
# convert them). This is the base for non-converting converters, which still
# serve to classify fields.
class _NonConverter(_FieldConverter):
    def convert(self, opts, value):
        return value

class _String(_NonConverter):
    pass

# Record keys show up in a few places, and look like hex identifiers.
# Converting them from hex is probably not useful. Not sure what to do, so for
# now they are non-converted.
class _RecordKey(_NonConverter):
    pass

class _Utf16(_NonConverter):
    pass

class _MessageId(_NonConverter):
    pass

# Meta-data shouldn't be converted because it might be important for
# interpreting data later on.
class _Meta(_NonConverter):
    pass

class _Int(_FieldConverter):
    def __init__(self, base):
        self._base = base

    def convert(self, opts, value):
        return unicode(self._to_int(value))

    def _to_int(self, value):
        return int(value, self._base)

# Decimal integers don't need conversion, but we still want to derive from _Int
# for classification purposes.
class _DecimalInt(_Int):
    def __init__(self):
        _Int.__init__(self, 10)

    def convert(self, opts, value):
        return value

class _SignedInt32(_Int):
    def convert(self, opts, value):
        ival = self._to_int(value)
        assert ival <= 0xffffffff, 'integer too large for 32 bits'
        if ival > 0x7fffffff:
            ival -= 0x100000000

        return unicode(ival)

class _HexChar(_FieldConverter):
    def convert(self, opts, value):
        # XXX
        pass

class _Flags(_Int):
    def __init__(self, values, empty=u'', base=16):
        _Int.__init__(self, base)

        self._empty = empty
        self._values = list(values)

    def convert(self, opts, value):
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

        flags.append('Priorities:%s' % self._priority_labels[priorities])
        flags.append('Labels:%X' % labels)

        return u' '.join(flags)

class _Enumeration(_Int):
    def __init__(self, values, default=None, base=16):
        _Int.__init__(self, base)

        if isinstance(values, dict):
            self._map = dict(values)
        else:
            self._map = dict(enumerate(values))

        self._default = default

    def convert(self, opts, value):
        ival = self._to_int(value)
        result = self._map.get(ival, self._default)
        if result is None:
            # No conversion
            return value
        else:
            return result

class _BoolInt(_Enumeration):
    def __init__(self):
        _Enumeration.__init__(self, [u'false', u'true'])

# This is for fields that signal something by their mere presence. The value
# doesn't matter.
class _BoolAnyVal(_FieldConverter):
    def convert(self, opts, value):
        return u'true'

class _Time(_FieldConverter):
    def _format(self, opts, t):
        return time.strftime(opts.time_format, t)

class _Seconds(_Time):
    def __init__(self, base=10, divisor=1):
        self._base = base
        self._divisor = divisor

    def convert(self, opts, value):
        # 0 is a common value, and obviously doesn't repressent a valid time.
        if value == '0':
            return value

        seconds = int(value, self._base) / self._divisor
        t = time.localtime(seconds)

        return self._format(opts, t)

class _FormattedTime(_Time):
    def __init__(self, parse_format):
        self._parse_format = parse_format

    def convert(self, opts, value):
        t = time.strptime(value, self._parse_format)
        return self._format(opts, t)

_string_converter = _String()
_record_key_converter = _RecordKey()
_utf16_converter = _Utf16()
_message_id_converter = _MessageId()
_meta_converter = _Meta()
_hex_int_converter = _Int(base=16)
_decimal_int_converter = _DecimalInt()
_signed_int32_converter = _SignedInt32()
_msg_flags_converter = _MsgFlags()
_bool_int_converter = _BoolInt()
_bool_any_converter = _BoolAnyVal()
_seconds_converter = _Seconds()
_hex_seconds_converter = _Seconds(base=16)
_microseconds_converter = _Seconds(divisor=1000000)

# The big dictionary of field converters.

_converters = {
    'm' : {
        # Source references are for Thunderbird 3.0.5 unless otherwise
        # indicated.

        # These are all declared in mailnews/db/msgdb/src/nsMsgDatabase.cpp
        # and read in in mailnews/db/msgdb/src/nsMsgThread.cpp
        # InitCachedValues.
        'children'            : _hex_int_converter,
        'threadFlags'         : _msg_flags_converter,
        'threadId'            : None,
        'threadNewestMsgDate' : _hex_seconds_converter,
        'threadRoot'          : None,
        'unreadChildren'      : _hex_int_converter,
    },
    'ns:addrbk:db:row:scope:card:all' : {
        # Source references are for Thunderbird 3.0.5 unless otherwise
        # indicated.

        # Most of the string types here can be found in
        # mailnews/addrbook/src/nsAddrDatabase.h in a call to
        # AddCharStringColumn.

        # mailnews/addrbook/src/nsAddrDatabase.h AddAllowRemoteContent
        'AllowRemoteContent'    : _bool_int_converter,
        'AnniversaryDay'        : _string_converter,
        'AnniversaryMonth'      : _string_converter,
        'AnniversaryYear'       : _string_converter,
        'BirthDay'              : _string_converter,
        'BirthMonth'            : _string_converter,
        'BirthYear'             : _string_converter,
        # Based on mailnews/addrbook/src/nsAddrDatabase.h AddCardType from
        # Thunderbird 2.0.0.24, CardType appears to be a string. However,
        # based on calls to GetCardTypeFromString in
        # mailnews/addrbook/src/nsAbCardProperty.cpp, and the definition of
        # constants in mailnews/addrbook/public/nsIAbCard.idl, it appears to be
        # an enumeration with a bizarre string-formatted integer internal
        # representation.
        'CardType'              : _Enumeration([u'normal', u'AOL groups',
                                                u'AOL additional email']),
        'Category'              : _string_converter,
        'CellularNumber'        : _string_converter,
        'CellularNumberType'    : _string_converter,
        'Company'               : _string_converter,
        'Custom1'               : _string_converter,
        'Custom2'               : _string_converter,
        'Custom3'               : _string_converter,
        'Custom4'               : _string_converter,
        'DefaultAddress'        : _string_converter,
        # mailnews/addrbook/src/nsAddrDatabase.h AddDefaultEmail (Thunderbird
        # 2.0.0.24). There's some indication that this is actually an
        # enumeration using AB_DEFAULT_EMAIL_IS_* constants in
        # mailnews/addrbook/public/nsIAbCard.idl, but it looks like these were
        # never actually used. Not in Thunderbird 3.
        'DefaultEmail'          : _string_converter,
        'Department'            : _string_converter,
        'DisplayName'           : _string_converter,
        'FamilyName'            : _string_converter,
        'FaxNumber'             : _string_converter,
        'FaxNumberType'         : _string_converter,
        'FirstName'             : _string_converter,
        'HomeAddress'           : _string_converter,
        'HomeAddress2'          : _string_converter,
        'HomeCity'              : _string_converter,
        'HomeCountry'           : _string_converter,
        'HomePhone'             : _string_converter,
        'HomePhoneType'         : _string_converter,
        'HomeState'             : _string_converter,
        'HomeZipCode'           : _string_converter,
        'JobTitle'              : _string_converter,
        # mailnews/addrbook/src/nsAddrDatabase.cpp AddRowToDeletedCardsTable
        'LastModifiedDate'      : _hex_seconds_converter,
        'LastName'              : _string_converter,
        # mailnews/addrbook/src/nsAddrDatabase.cpp AddPrimaryEmail
        'LowercasePrimaryEmail' : _string_converter,
        'NickName'              : _string_converter,
        'Notes'                 : _string_converter,
        'PagerNumber'           : _string_converter,
        'PagerNumberType'       : _string_converter,
        'PhoneticFirstName'     : _string_converter,
        'PhoneticLastName'      : _string_converter,
        'PopularityIndex'       : _hex_int_converter,
        # mailnews/addrbook/src/nsAbCardProperty.cpp ConvertToEscapedVCard
        'PreferMailFormat'      : _Enumeration([u'unknown', u'plaintext',
                                                u'html']),
        # mailnews/addrbook/src/nsAddrDatabase.cpp AddPrimaryEmail
        'PrimaryEmail'          : _string_converter,
        'RecordKey'             : _record_key_converter,
        'SecondEmail'           : _string_converter,
        'SpouseName'            : _string_converter,
        'WebPage1'              : _string_converter,
        'WebPage2'              : _string_converter,
        'WorkAddress'           : _string_converter,
        'WorkAddress2'          : _string_converter,
        'WorkCity'              : _string_converter,
        'WorkCountry'           : _string_converter,
        'WorkPhone'             : _string_converter,
        'WorkPhoneType'         : _string_converter,
        'WorkState'             : _string_converter,
        'WorkZipCode'           : _string_converter,
        '_AimScreenName'        : _string_converter,
    },
    'ns:addrbk:db:row:scope:data:all' : {
        'LastRecordKey' : _record_key_converter,
    },
    'ns:addrbk:db:row:scope:list:all' : {
        # Source references are for Thunderbird 3.0.5 unless otherwise
        # indicated.

        # Most of the string types here can be found in
        # mailnews/addrbook/src/nsAddrDatabase.h in a call to
        # AddCharStringColumn.

        # Left out: 'Address1', 'Address2', etc.
        'ListDescription'    : _string_converter,
        # mailnews/addrbook/src/nsAddrDatabase.cpp AddListName
        'ListName'           : _string_converter,
        'ListNickName'       : _string_converter,
        # mailnews/addrbook/src/nsAddrDatabase.cpp GetListAddressTotal
        'ListTotalAddresses' : _hex_int_converter,
        # mailnews/addrbook/src/nsAddrDatabase.cpp AddListName
        'LowercaseListName'  : _string_converter,
        'RecordKey'          : _record_key_converter,
    },
    'ns:formhistory:db:row:scope:formhistory:all' : {
        'ByteOrder' : _meta_converter,
        # From any example file, it's obvious that Name and Value are strings.
        'Name'      : _string_converter,
        'Value'     : _string_converter,
    },
    'ns:history:db:row:scope:history:all' : {
        # Source references are from Firefox 2.0.0.20 unless otherwise
        # indicated.

        # Tokens are created in
        # /toolkit/components/history/src/nsGlobalHistory.cpp CreateTokens.
        # AddNewPageToDatabase in the same file is a good reference for these.

        'ByteOrder'      : _meta_converter,
        'FirstVisitDate' : _microseconds_converter,
        'Hidden'         : _bool_any_converter,
        'Hostname'       : _string_converter,
        'LastVisitDate'  : _microseconds_converter,
        # From /toolkit/components/history/src/nsGlobalHistory.cpp
        # SetPageTitle.
        'Name'           : _utf16_converter,
        'Referrer'       : _string_converter,
        'Typed'          : _bool_any_converter,
        'URL'            : _string_converter,
        # From /toolkit/components/history/src/nsGlobalHistory.cpp
        # AddExistingPageToDatabase.
        'VisitCount'     : _decimal_int_converter,
    },
    'ns:msg:db:row:scope:dbfolderinfo:all' : {
        # Source references are for Thunderbird 3.0.5 unless otherwise
        # indicated.

        # XXX mailnews/db/msgdb/src/nsDBFolderInfo.cpp might be where a lot of
        # these come from.

        # From mailnews/db/msgdb/src/nsMsgDatabase.cpp, SetStringProperty seems
        # to call the nsMsgDBFolder version, which seems to call the
        # nsMsgFolderCacheElement version.
        'LastPurgeTime'        : _FormattedTime('%a %b %d %H:%M:%S %Y'),
        # Defined in mailnews/base/public/msgCore.h, used
        # in mailnews/base/util/nsMsgDBFolder.cpp
        'MRUTime'              : _seconds_converter,
        # Defined in mailnews/db/msgdb/src/nsDBFolderInfo.cpp. Set with
        # nsMsgDatabase::UInt32ToRowCellColumn. Based on usage in
        # mailnews/imap/src/nsImapMailFolder.cpp, can be kUidUnknown (-1).
        # I *think* this comes from the IMAP protocol, and is just an integer.
        'UIDValidity'          : _signed_int32_converter,
        # From mailnews/db/msgdb/src/nsDBFolderInfo.cpp.
        'charSet'              : _string_converter,
        # From mailnews/db/msgdb/src/nsDBFolderInfo.cpp.
        'charSetOverride'      : _bool_int_converter,
        # From mailnews/db/msgdb/src/nsMsgDatabase.cpp
        'cleanupBodies'        : _bool_int_converter,
        # current-view and current-view-tag seem to have duplicate definitions
        # in suite/mailnews/msgViewPickerOverlay.js and
        # mail/base/modules/mailViewManager.js.
        'current-view'         : _Enumeration([
                                    u'kViewItemAll', u'kViewItemUnread',
                                    u'kViewItemTags', u'kViewItemNotDeleted',
                                    None, None, None, u'kViewItemVirtual',
                                    u'kViewItemCustomize',
                                    u'kViewItemFirstCustom',
                                 ]),
        'current-view-tag'     : None,
        'daysToKeepBodies'     : None,
        'daysToKeepHdrs'       : None,
        'expungedBytes'        : None,
        'fixedBadRefThreading' : None,
        'flags'                : None,
        'folderDate'           : None,
        'folderName'           : None,
        'folderSize'           : None,
        'highWaterKey'         : None,
        'imapFlags'            : None,
        'keepUnreadOnly'       : None,
        'knownArts'            : None,
        'mailboxName'          : None,
        'numHdrsToKeep'        : None,
        'numMsgs'              : None,
        'numNewMsgs'           : None,
        'onlineName'           : None,
        'readSet'              : None,
        'retainBy'             : None,
        'sortColumns'          : None,
        'sortOrder'            : None,
        'sortType'             : None,
        'useServerDefaults'    : None,
        'version'              : None,
        'viewFlags'            : None,
        'viewType'             : None,
    },
    'ns:msg:db:row:scope:folders:all' : {
        'LastPurgeTime'     : None,
        'MRUTime'           : None,
        'aclFlags'          : None,
        'boxFlags'          : None,
        'charset'           : None,
        'expungedBytes'     : None,
        'flags'             : None,
        'folderName'        : None,
        'folderSize'        : None,
        'hierDelim'         : None,
        'key'               : None,
        'onlineName'        : None,
        'pendingMsgs'       : None,
        'pendingUnreadMsgs' : None,
        'totalMsgs'         : None,
        'totalUnreadMsgs'   : None,
    },
    'ns:msg:db:row:scope:msgs:all' : {
        'ProtoThreadFlags'    : None,
        'account'             : None,
        'ccList'              : None,
        'date'                : None,
        'dateReceived'        : None,
        'flags'               : None,
        'junkpercent'         : None,
        'junkscore'           : None,
        'junkscoreorigin'     : None,
        'keywords'            : None,
        'label'               : None,
        'message-id'          : None,
        'msgCharSet'          : None,
        'msgOffset'           : None,
        'msgThreadId'         : None,
        'numLines'            : None,
        'numRefs'             : None,
        'offlineMsgSize'      : None,
        'preview'             : None,
        'priority'            : None,
        'recipients'          : None,
        'references'          : None,
        'remoteContentPolicy' : None,
        'replyTo'             : None,
        'sender'              : None,
        'size'                : None,
        'statusOfset'         : None,
        'subject'             : None,
        'threadParent'        : None,
    },
    'ns:msg:db:row:scope:threads:all' : {
        'threadSubject' : None,
    },
}

class FieldConverter(Filter):
    '''
    Filter to interpret Mork fields, making them more human-readable.
    '''
    def __init__(self, order):
        self.mork_filter_order = order

    def add_options(self, parser):
        parser.add_option('--no-convert', action='store_true',
            help="don't do usual field conversions")

        # XXX
        parser.add_option('--time-format', metavar='FORMAT',
            help='use FORMAT as the strftime format for times/dates '
                 '(default: %c)')
        parser.set_defaults(time_format='%c')

    def process(self, db, opts):
        if opts.no_convert:
            return

        for (row_namespace, row_id, row) in db.rows.items():
            row_converters = _converters.get(row_namespace)
            if row_converters is None:
                continue

            for (col, value) in row.items():
                converter = row_converters.get(col)
                if converter:
                    row[col] = converter.convert(opts, value)

convert_fields = FieldConverter(4600)
