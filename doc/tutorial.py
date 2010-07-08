# Copyright 2009, 2010 Kevin Goodsell

# Tutorial for Writing Filters
#
# This is a tutorial in the form of a real output filter module -- you can
# actually drop it into the MorkDB/filters directory and use it as-is.

import sys

# The Filter class isn't actually required for writing filters, but it
# describes the basic interface and is kind of handy.
from filterbase import Filter
# EncodingStream is a helper for doing output in whatever character encoding
# the user asks for.
from encoding import EncodingStream

# All filters require three items:
#   mork_filter_order - an integer value used for identifying and ordering
#                       filters.
#   add_options       - a function/method that the filter can use to provide
#                       or modify command-line options.
#   process           - the function/method that does all the real work.

# It's probably more convenient in general for class *instances* to represent
# filters, but the class itself can also work. This example will show how this
# is done. There are several examples of instance-based filters in the source.
class TutorialFilter(Filter):
    '''Demonstration filter that produces simple text output.'''
    # The mork_filter_order attribute provides the ordering for filters:
    # the lower the order, the earlier the filter is run. A negative value
    # can be used to disable a filter, or in cases where a class is intended
    # as a base class for filters rather than a filter itself. The 'Filter'
    # class is an example of this.
    #
    # See filterbase.py for a description of the conventions used for order
    # values.
    #
    # Here, we use a low order value in the range of "output" filters, which
    # begins at 10000. Since generally only one output filter actually does
    # output, the higher-order filters take precedence (since they have the
    # final say in setting default options).
    mork_filter_order = 10001

    # add_options is invoked early during construction of the
    # optparser.OptionParser instance. This allows filters to provide their
    # own command-line options, and sometimes to override default option
    # values. See the optparse documentation for full details of how to add
    # and use options.
    #
    # For an class instance-based filter, this would be a normal method rather
    # than a classmethod.
    @classmethod
    def add_options(cls, parser):
        # This adds an option '--text' that, if given, sets the option
        # out_format to the value 'text'. This is the normal way of selecting
        # an output format.
        parser.add_option('--text', dest='out_format', action='store_const',
            const='text', help='write simple text output')
        # This adds a '--tabs' option that, if given, causes tabs to be used
        # for indentation.
        parser.add_option('--tabs', action='store_true',
            help='use tabs instead of spaces for simple text output')

        # Typically an output filter should set out_format to the value it
        # recognizes. Higher-order filters will just override it, and the
        # highest will become the final default. This way when a filter is
        # removed we gracefully fall back on the next-highest priority filter.
        parser.set_defaults(out_format='text')

    # process does the real work.
    @classmethod
    def process(cls, db, opts):
        # The process function always gets called for each filter, so it's up
        # to the filter to check opts and determine if it actually has
        # anything to do.
        if opts.out_format != 'text':
            return

        # That covers the basics of the output filter API. The rest of the work
        # involves interpreting the MorkDatabase contents and writing the
        # result. This part is not as straight-forward, because it requires
        # some understanding of the MorkDatabase class's internals.

        # outname is a common option for describing the output name (file,
        # directory, or whatever). Here we use '-' or the absence of outname
        # to select stdout.
        outname = opts.outname or '-'
        if outname == '-':
            f = EncodingStream(opts.out_encoding, sys.stdout)
        else:
            f = EncodingStream.open(opts.out_encoding, outname)

        if opts.tabs:
            indent = '\t'
        else:
            indent = '    '

        # Basic iteration over tables generally looks like this. db.tables is a
        # customized dict where the keys are always (namespace, oid) tuples.
        # The items() method is modified to reflect this, returning the key
        # components separately.
        for (namespace, oid, table) in db.tables.items():
            # This simple example completely skips meta-tables. I don't
            # recommend this in general, since they may contain useful data.
            cls._write_table(f, namespace, oid, table, indent)

    @classmethod
    def _write_table(cls, f, namespace, oid, table, indent):
        print >> f, 'TABLE (namespace: %s, id: %s)' % (namespace, oid)

        # A table is a customized list type where the items are 3-tuples of
        # (namespace, id, row). This allows iteration similar to the iteration
        # over db.tables, but the items() method is not used.
        for (row_namespace, row_id, row) in table:
            cls._write_row(f, row_namespace, row_id, row, indent)

    @classmethod
    def _write_row(cls, f, namespace, oid, row, indent):
        print >> f, '%sROW (namespace: %s, id: %s)' % (indent, namespace, oid)

        # A MorkRow is a dict mapping column names to cell values.
        for (column, value) in row.items():
            print >> f, '%s%s = %s' % (indent * 2, column, value)
