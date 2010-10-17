#!/usr/bin/env python
# Copyright 2009, 2010 Kevin Goodsell
#
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

# Do python version checking up front.
import sys

min_python_version = (2, 4)
if sys.version_info < min_python_version:
    str_version = '.'.join([str(part) for part in min_python_version])
    print >> sys.stderr, ('This script requires python %s or higher!' %
                          str_version)
    sys.exit(1)

# Done with version checking. Get on with real work.

import optparse
import re
import warnings
import os

from MorkDB.filters import enumerate_filters, list_filters

version = '2.2'

# Override warning format, copy-paste from warnings.py with changes.
def _show_warning(message, category, filename, lineno, file=None, line=None):
    if file is None:
        file = sys.stderr
    try:
        # Copied from warnings.py:formatwarning and modified.
        shortened = os.path.relpath(filename)
        if len(filename) < len(shortened):
            shortened = filename
        s = "%s:%s: %s: %s\n" % (shortened, lineno, category.__name__, message)
        file.write(s)
    except IOError:
        pass # the file (probably stderr) is invalid - this warning gets lost.

warnings.showwarning = _show_warning

def print_tokens(f):
    import MorkDB.morklex as morklex
    morklex.print_tokens(f)

def print_syntax_tree(f):
    import MorkDB.morkyacc as morkyacc
    tree = morkyacc.parse_file(f)
    print tree

_leading_space_matcher = re.compile(r'^\s+', re.MULTILINE)
def _format_docstring(docstring, indent):
    s = docstring.strip()
    return indent + _leading_space_matcher.sub(indent, s)

def print_filters():
    for (order, filt) in enumerate_filters():
        if hasattr(filt, '__name__'):
            name = filt.__name__
        else:
            name = filt.__class__.__name__

        print '%5d - %s' % (order, name)

        if filt.__doc__:
            print _format_docstring(filt.__doc__, ' '*10)

def process_database(f, filters, opts):
    import MorkDB.morkdb as morkdb
    import MorkDB.morkyacc as morkyacc

    tree = morkyacc.parse_file(f)
    db = morkdb.MorkDatabase.from_ast(tree)

    for filt in filters:
        filt.process(db, opts)

def parse_arguments(args, filters):
    parser = optparse.OptionParser(usage='%prog [options] [<mork-file>]',
        version='Mork converter by Kevin Goodsell, version %s' % version)

    parser.add_option('-o', '--outname', help='output file or dir name')
    parser.add_option('-e', '--out-encoding', metavar='ENCODING',
        help="use ENCODING as the output encoding (e.g., utf-16)")

    for f in filters:
        f.add_options(parser)

    debug_group = optparse.OptionGroup(parser, 'Debug Options')
    debug_group.add_option('--tokens', dest='out_format', action='store_const',
        const='tokens', help='just print lexical tokens')
    debug_group.add_option('--syntax', dest='out_format', action='store_const',
        const='syntax', help='just print abstract syntax')
    debug_group.add_option('--filters', dest='out_format',
        action='store_const', const='filters',
        help='just list available filters')
    parser.add_option_group(debug_group)

    parser.set_defaults(out_encoding='utf-8')

    (options, arguments) = parser.parse_args(args)

    if len(arguments) > 1:
        parser.error('too many file arguments')

    return (options, arguments)

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    filters = list_filters()
    (opts, arguments) = parse_arguments(args, filters)

    if len(arguments) == 0:
        f = sys.stdin
    else:
        f = arguments[0]

    if opts.out_format == 'tokens':
        print_tokens(f)
    elif opts.out_format == 'syntax':
        print_syntax_tree(f)
    elif opts.out_format == 'filters':
        print_filters()
    else:
        process_database(f, filters, opts)

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
    except IOError, e:
        import errno
        if e.errno != errno.EPIPE:
            raise
