'''
Copyright 2009, 2010 Kevin Goodsell

morklex.py -- PLY-based lexical analyzer for Mork database files.
'''

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

import ply.lex as lex
import re
import sys

tokens = (
    # 'Special' tokens
    'MAGIC',
    #'COMMENT',

    # Dict tokens
    'LANGLE',
    'RANGLE',

    # Common tokens
    'HEX',
    'NAME',
    'CARET',
    'COLON',

    # Cell/Alias tokens
    'LPAREN',
    'RPAREN',
    'VALUE',

    # Wierd group stuff
    'GROUPSTART',
    'GROUPCOMMIT',
    'GROUPABORT',
)

# These tokens can be ambiguous:
# HEX, NAME
# COLON, NAME
# VALUE and almost any other token

# Cells are by far the trickiest part of all this.
#
# "Cells" can be divided into dict aliases and (meta/row) cells.
# Alias is: '(' hex '=' value ')'
# Cell is: '(' ( '^' mid | name ) ( '^' mid | '=' value ) ')'
# where mid is: hex | hex ':' name | hex ':^' hex

states = (
    # dict and metadict are necessary just to distinguish cells from
    # aliases -- in a dict it's an alias, unless it's in a metadict.
    ('dict', 'exclusive'),
    ('metadict', 'exclusive'),
    ('alias', 'exclusive'),
    ('cell', 'exclusive'),
    ('name', 'exclusive'), # name or object reference
    ('id', 'exclusive'),
)

# 'Special' tokens
def t_MAGIC(t):
    r'//\ <!--\ <mdb:mork:z\ v="1\.4"/>\ -->[^\r\n]*'
    return t

def t_dict_metadict_INITIAL_COMMENT(t):
    r'//[^\r\n]*'
    pass

# Dict tokens
def t_LANGLE(t):
    r'<'
    t.lexer.push_state('dict')
    return t

def t_dict_LPAREN(t):
    r'\('
    t.lexer.push_state('alias')
    return t

def t_dict_LANGLE(t):
    r'<'
    t.lexer.push_state('metadict')
    return t

def t_dict_metadict_RANGLE(t):
    r'>'
    t.lexer.pop_state()
    return t

# Cell and alias tokens
def t_metadict_INITIAL_LPAREN(t):
    r'\('
    t.lexer.push_state('cell')
    t.lexer.push_state('name')
    return t

def t_alias_cell_RPAREN(t):
    r'\)'
    t.lexer.pop_state()
    return t

def t_cell_CARET(t):
    r'\^'
    t.lexer.push_state('id')
    return t

def t_alias_cell_VALUE(t):
    r'''=  # XXX I'd like to remove this, but I'm not sure that's allowed.
    ( [^)\\]    # Anything that's not \ or )
    | \\[)\\$]  # Basic escapes
    | \\\r?\n   # Line continuation
    | \\\r      # Line continuation for Macs
    )* '''
    newlines = t.value.count('\n')
    if newlines == 0:
        newlines = t.value.count('\r')
    t.lexer.lineno += newlines
    t.value = t.value[1:]
    return t

# Handling of 'name' state.
def t_name_CARET(t):
    r'\^'
    t.lexer.begin('id')
    return t

def t_name_NAME(t):
    r'[A-Za-z_:][-A-Za-z_:!?+]*'
    t.lexer.pop_state()
    return t

def t_id_HEX(t):
    r'[0-9a-fA-F]+'
    t.lexer.pop_state()
    return t

# Common tokens
def t_alias_INITIAL_HEX(t):
    r'[0-9a-fA-F]+'
    return t

def t_cell_INITIAL_COLON(t):
    r':'
    t.lexer.push_state('name')
    return t

# Group tokens
t_GROUPSTART =  r'@\$\$\{[0-9a-fA-F]+\{@'
t_GROUPCOMMIT = r'@\$\$\}[0-9a-fA-F]+\}@'
# According to documentation, group aborts look like this:
#   '@$$}~abort~' objid '}@'
# But according to the code, aborts are expected to simply be '@$$}~~}@'.
t_GROUPABORT =  r'@\$\$\}(~abort~[0-9a-fA-F]+|~~)\}@'

# Special rules

t_ANY_ignore = ' \t'

literals = '[]{}-+!'

def t_ANY_newline(t):
    r'(\r?\n)+'
    t.lexer.lineno += t.value.count('\n')

def t_ANY_mac_newline(t):
    r'\r+'
    t.lexer.lineno += len(t.value)

def t_ANY_error(t):
    print >> sys.stderr, "Lexing error at line %d, next chars: %r" % (
        t.lexer.lineno, t.value[:10])
    t.lexer.skip(1)

lex.lex(reflags=re.MULTILINE|re.VERBOSE)

def print_tokens(f):
    if isinstance(f, basestring):
        f = open(f)

    lex.input(f.read())
    while True:
        tok = lex.token()
        if not tok:
            break
        print tok
