# Copyright 2010 Kevin Goodsell

# Output filter for writing Mork databases in XML format. This is also a basic
# introduction to writing output filters.
#
# For reference, the XML 1.0 specification is available here:
# http://www.w3.org/TR/2008/REC-xml-20081126/

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

import re
import warnings
import sys

from filterbase import Filter
from encoding import EncodingStream

# Filter is available as a base class for filter classes, but it's not
# necessary. Filters can be classes or class instances. In this case it
# will be an instance.
class XmlOutput(Filter):
    '''Filter to produce XML output.'''
    def __init__(self, order, indent_str='    '):
        # REQUIRED: All filters, whether class or instance, must have a
        # mork_filter_order attribute, and the value must be non-negative for
        # the filter to actually be used. Filters are applied in the order
        # dictated by these attributes.
        self.mork_filter_order = order
        self._indent_str = indent_str

    # REQUIRED: All filters have an add_options method. It takes an instance
    # of optparse.OptionParser, and should add any filter-specific options.
    # While this is required, a no-op version is provided in Filter, so when
    # deriving from Filter it's OK to not provide your own if there are no
    # options to add.
    def add_options(self, parser):
        # out_format is an option used globally to choose output format. It's
        # value is just a string identifier that some filter should recognize.
        parser.add_option('--xml', dest='out_format', action='store_const',
            const='xml', help='output XML (default)')

        # Filters for doing output should usually set the out_format option
        # value to whatever format they recognize. This way, the default
        # output format is selected from the highest priority filter
        # automatically.
        parser.set_defaults(out_format='xml')

    # REQUIRED: All filters have a process method. It takes a MorkDatabase
    # instance and the options from the optparse.OptionParser. This is where
    # the actual work is done. A filter that is disabled (by options or by
    # default) should just return. A filter that modifies the database should
    # do it in place. Output filters should read the database and do output.
    def process(self, db, opts):
        if opts.out_format != 'xml':
            return

        if opts.outname is None or opts.outname == '-':
            f = EncodingStream(opts.out_encoding, sys.stdout)
        else:
            f = EncodingStream.open(opts.out_encoding, opts.outname)

        self._output(db, f)

    def _output(self, db, f):
        print >> f, '<?xml version="1.0"?>'
        print >> f, '<morkxml>'

        for (namespace, oid, table) in db.tables.items():
            meta = db.meta_tables.get((namespace, oid))
            self._write_table(f, namespace, oid, table, meta)

        print >> f, '</morkxml>'

    def _write_table(self, f, namespace, oid, table, meta=None, indent=1):
        indent_str = self._indent_str * indent
        print >> f, '%s<table namespace=%s id=%s>' % (indent_str,
            self._format_attribute(namespace), self._format_attribute(oid))

        for (row_namespace, row_id, row) in table:
            self._write_row(f, row_namespace, row_id, row, indent + 1)

        if meta is not None:
            self._write_meta_table(f, meta, indent + 1)

        print >> f, '%s</table>' % indent_str

    def _write_meta_table(self, f, meta, indent):
        indent_str = self._indent_str * indent
        print >> f, '%s<metatable>' % indent_str

        for (column, value) in meta.cells.items():
            self._write_cell(f, column, value, indent + 1)

        for (namespace, oid, row) in meta.rows:
            self._write_row(f, namespace, oid, row, indent + 1)

        print >> f, '%s</metatable>' % indent_str

    def _write_row(self, f, namespace, oid, row, indent):
        indent_str = self._indent_str * indent
        print >> f, '%s<row namespace=%s id=%s>' % (indent_str,
            self._format_attribute(namespace), self._format_attribute(oid))

        for (column, value) in row.items():
            self._write_cell(f, column, value, indent + 1)

        print >> f, '%s</row>' % indent_str

    def _write_cell(self, f, column, value, indent):
        indent_str = self._indent_str * indent
        print >> f, '%s<cell column=%s>%s</cell>' % (indent_str,
            self._format_attribute(column), self._format_element_text(value))

    # Regex for stuff that's not in the 'Char' production of the XML grammar
    _non_char = (
        u'['
        u'\x00-\x08\x0B\x0C\x0E-\x1F'  # Control characters
        u'\uD800-\uDFFF'               # Surrogates
        u'\uFFFE\uFFFF'                # Permanently unassigned (BOM)
        u']'
    )

    # Regex for stuff that's not in the 'AttValue' production in the XML
    # grammar. '>' is also included for symmetry.
    _non_att_value_matcher = re.compile(_non_char + u'|[<>&"]')

    # Regex for stuff that's not in the 'CharData' production in the XML
    # grammar. '>' is also included for symmetry.
    _non_char_data_matcher = re.compile(_non_char + u'|[<>&]')
    # For reference, the version without '>' requires including ']]>':
    #_non_char_data_matcher = re.compile(_non_char + u'|[<&]|]]>')

    _replacements = {
        '<'   : '&lt;',
        '>'   : '&gt;',
        '&'   : '&amp;',
        '"'   : '&quot;',
        "'"   : '&apos;',
        ']]>' : ']]&gt;',
    }
    def _replacer(self, match):
        old = match.group()
        new = self._replacements.get(old)
        if new is None:
            warnings.warn('found invalid XML characters; this will not be a '
                          'well-formed XML document')
            # Use a CharRef even though it's not well-formed, since CharRefs
            # don't get around the character limitations in XML.
            new = '&#x%x;' % ord(old)

        return new

    def _format_attribute(self, value):
        # This corresponds to 'AttValue' in the spec.
        return '"%s"' % self._non_att_value_matcher.sub(self._replacer, value)

    def _format_element_text(self, value):
        # This correspond to 'CharData' in the spec.
        return self._non_char_data_matcher.sub(self._replacer, value)

# Since XML is to be the default output, its order should be the highest.
# This makes it the last filter to have add_options called, and therefore it
# gets the final word on option defaults.
xml_filter = XmlOutput(10200)
