import ply.lex as lex
import re
import sys

tokens = (
    # 'Special' tokens
    'MAGIC',
    #'COMMENT',

    # Common tokens
    'OBJREF',
    'OBJID',
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
    r'//\ <!--\ <mdb:mork:z\ v="1\.4"/>\ -->$'
    return t

def t_COMMENT(t):
    r'//.*$'
    pass

# Common tokens
t_ANY_OBJREF = r'\^[0-9a-fA-F]+'

def t_OBJID(t):
    r'[0-9a-fA-F]+'
    return t

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
    ( [^)\\]  # Anything that's not ) or \
    | \\\\    # ...or \\
    | \\\)    # ...or \)
    | \\\n    # ...or \nl
    )* '''
    newlines = t.value.count('\n')
    t.lexer.lineno += newlines
    t.value = t.value[1:]
    return t


# Wierd group stuff
t_GROUPSTART =  r'@\$\$\{[0-9a-fA-F]+\{@'
t_GROUPCOMMIT = r'@\$\$\}[0-9a-fA-F]+\}@'
t_GROUPABORT =  r'@\$\$\}~abort~[0-9a-fA-F]+\}@'

# Special rules

t_ANY_ignore = ' \t'

literals = '<>[]{}:'

def t_ANY_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_ANY_error(t):
    print >> sys.stderr, "Lexing error at line %d, next chars: %r" % (
        t.lexer.lineno, t.value[:10])
    t.lexer.skip(1)

lex.lex(reflags=re.MULTILINE)

if __name__ == '__main__':
    lex.runmain()
