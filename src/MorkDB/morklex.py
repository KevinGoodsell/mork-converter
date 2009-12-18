'''
Copyright (c) 2009 Kevin Goodsell

morklex.py -- PLY-based lexical analyzer for Mork database files.
'''
import ply.lex as lex
import re
import sys

tokens = (
    # 'Special' tokens
    'MAGIC',
    #'COMMENT',

    # Common tokens
    'LITERAL',

    # Cell tokens
    'LPAREN',
    'RPAREN',
    'VALUE',

    # Wierd group stuff
    'GROUPSTART',
    'GROUPCOMMIT',
    'GROUPABORT',
)

states = (
    ('cell', 'exclusive'),
)

# 'Special' tokens
def t_MAGIC(t):
    r'//\ <!--\ <mdb:mork:z\ v="1\.4"/>\ -->[^\r\n]*'
    return t

def t_COMMENT(t):
    r'//[^\r\n]*'
    pass

# Common tokens
def t_ANY_LITERAL(t):
    r'[a-zA-Z_0-9]+' # XXX Not really accurate
    return t

# Cell tokens
def t_LPAREN(t):
    r'\('
    t.lexer.push_state('cell')
    return t

def t_cell_RPAREN(t):
    r'\)'
    t.lexer.pop_state()
    return t

def t_cell_VALUE(t):
    r'''=
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


# Wierd group stuff
t_GROUPSTART =  r'@\$\$\{[0-9a-fA-F]+\{@'
t_GROUPCOMMIT = r'@\$\$\}[0-9a-fA-F]+\}@'
t_GROUPABORT =  r'@\$\$\}~abort~[0-9a-fA-F]+\}@'

# Special rules

t_ANY_ignore = ' \t'

literals = '<>[]{}:-+!^'

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

lex.lex(reflags=re.MULTILINE)

def printTokens(f):
    if isinstance(f, basestring):
        f = open(f)

    lex.input(f.read())
    while True:
        tok = lex.token()
        if not tok:
            break
        print tok
