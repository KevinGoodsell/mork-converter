# Copyright (c) 2009 Kevin Goodsell

# Tutorial for Writing Output Filters
#
# This is a tutorial in the form of a real output filter module -- you can
# actually drop it into the MorkDB/filter/output directory and use it as-is.
#
# The util module contains some handy but optional things. It also contains
# the ArgumentError exception class, used to indicate problems with the filter
# arguments. You don't even need this import if you don't want to signal any
# argument errors, but it's certainly good to have.
import MorkDB.filter.util as util
#
# All output filters require four items: _MORK_OUTPUT_FILTER, description,
# usage, and output. Descriptions and examples of each follow.
#
# _MORK_OUTPUT_FILTER must exist, but its value does not matter. This simply
# identifies the module as an output filter.
_MORK_OUTPUT_FILTER = True
#
# description must exist, but won't be used if it is empty, None, or otherwise
# evaluates to False. Should be a basic description of the filter.
description = 'Tutorial output filter'
#
# usage must exist, and provides the names and descriptions for arguments that
# are accepted by the output filter.
usage = [
    ('out', 'Name of file to write to'),
    ('tabs', 'Use tabs instead of spaces for indentation'),
]
#
# This is the simplest way of providing the arguments, but using util.Argument
# instances instead of tuples is probably more convenient. Here is what this
# would look like:
#usage = [
#    util.Argument('out', 'Name of file to write to'),
#    util.Argument('tabs', 'Use tabs instead of spaces for indentation',
#                  util.convertBool),
#]
#
# Note the addition of util.convertBool, a converter for the 'tabs' argument.
# This is just a function that takes a string and returns a bool to allow
# automatic conversion of argument strings to a more useful type. The 'out'
# parameter needs no conversion, since the expected type is the same as the
# initial type: str.
#
# The convertBool function allows some common words to be given for 'True' or
# 'False', but more commonly it converts an empty string to 'True'. This allows
# the option to be given without an explicit value. E.g., the argument 'tabs'
# has the same effect as 'tabs=yes'.
#
# The final required item is the 'output' function, which takes two arguments.
# The first argument is a MorkDatabase instance. The second argument is a dict
# of filter arguments with the argument names as the keys and the argument text
# as the values.
def output(db, args):
    # Handling the arguments manually is tedious, which is one reason why you
    # may want to use util.Argument and util.convertArgs instead.
    out = None
    tabs = False
    for (name, value) in args.items():
        if name == 'out':
            out = value
        elif name == 'tabs':
            tabs = True
        else:
            raise util.ArgumentError('Unknown argument: %s' % name)

    if out is None:
        raise util.ArgumentError("Missing required argument 'out'")

    _outputHelper(db, out, tabs)

    # Doing something similar using util.Arguments and util.convertArgs looks
    # like this:
    #args = util.convertArgs(usage, args)
    #if 'out' not in args:
    #    raise util.ArgumentError("Missing required argument 'out'")
    #_outputHelper(db, **args)

# That covers the basics of the output filter API. The rest of the work
# involves interpreting the MorkDatabase contents and writing the result. This
# part is not as straight-forward, because it requires some understanding of
# the MorkDatabase class's internals.

def _outputHelper(db, out, tabs=False):
    f = open(out, 'w')

    if tabs:
        indent = '\t'
    else:
        indent = '    '

    # Basic iteration over tables generally looks like this. db.tables is a
    # customized dict where the keys are always (namespace, oid) tuples. The
    # items() method is modified to reflect this, returning the key components
    # separately.
    for (namespace, oid, table) in db.tables.items():
        # This simple example completely skips meta-tables. I don't recommend
        # this in general, since they may contain useful data.
        _writeTable(f, namespace, oid, table, indent)

    f.close()

def _writeTable(f, namespace, oid, table, indent):
    print >> f, 'TABLE (namespace: %s, id: %s)' % (namespace, oid)

    # A table is a customized list type where the items are 3-tuples of
    # (namespace, id, row). This allows iteration similar to the iteration
    # over db.tables, but the items() method is not used.
    for (rowNamespace, rowId, row) in table:
        _writeRow(f, rowNamespace, rowId, row, indent)

def _writeRow(f, namespace, oid, row, indent):
    print >> f, '%sROW (namespace: %s, id: %s)' % (indent, namespace, oid)

    # A MorkRow is a dict mapping column names to cell values.
    for (column, value) in row.items():
        print >> f, '%s%s = %s' % (indent * 2, column, value)
