'''
Copyright 2009, 2010 Kevin Goodsell

morkyacc.py -- PLY-based parser for Mork database files.
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

import re
import ply.yacc as yacc
import warnings

from MorkDB.morklex import tokens
import MorkDB.morkast as morkast

def p_mork_db(p):
    '''
    mork : MAGIC item_group_list
         | item_group_list
    '''
    if len(p) == 2:
        # No magic found
        warnings.warn('File may not be a supported mork version')
        items = p[1]
    else:
        items = p[2]

    p[0] = morkast.Database(items)

def p_item_or_group(p):
    '''
    item_group : item
               | group
    '''
    p[0] = p[1]

def p_item_group_list(p):
    '''
    item_group_list :
                    | item_group_list item_group
    '''
    if len(p) == 1:
        p[0] = []
    else:
        p[0] = p[1] + [ p[2] ]

def p_item(p):
    '''
    item : dict
         | row
         | table
    '''
    p[0] = p[1]

def p_item_list(p):
    '''
    item_list :
              | item_list item
    '''
    if len(p) == 1:
        p[0] = []
    else:
        p[0] = p[1] + [ p[2] ]

_groupId = re.compile(r'@\$\$\{(?P<id>[0-9a-fA-F]+)\{@')
def p_group(p):
    '''
    group : GROUPSTART item_list GROUPCOMMIT
          | GROUPSTART item_list GROUPABORT
    '''
    m = _groupId.match(p[1])
    if m is None:
        raise ValueError('no ID found in group token: %s' % p[1])

    commit = p[3].find('~') == -1

    p[0] = morkast.Group(m.group('id'), p[2], commit)

def p_dict(p):
    '''
    dict : LANGLE dict_inner RANGLE
    '''
    p[0] = p[2]

def p_dict_inner_alias(p):
    '''
    dict_inner :
               | dict_inner alias
    '''
    if len(p) == 1:
        p[0] = morkast.Dict()
    else:
        p[1].aliases.append(p[2])
        p[0] = p[1]

def p_dict_inner_meta(p):
    '''
    dict_inner : dict_inner meta_dict
    '''
    p[1].meta.append(p[2])
    p[0] = p[1]

def p_alias(p):
    '''
    alias : LPAREN HEX VALUE RPAREN
    '''
    p[0] = morkast.Alias(p[2], p[3])

def p_meta_dict(p):
    '''
    meta_dict : LANGLE cell_list RANGLE
    '''
    p[0] = morkast.MetaDict(p[2])

def p_row(p):
    '''
    row : '[' object_id row_inner ']'
        | '[' '-' object_id row_inner ']'
    '''
    if len(p) == 6:
        trunc = True
        objid, inner = p[3:5]
    else:
        trunc = False
        objid, inner = p[2:4]

    p[0] = morkast.Row(objid, inner['cells'], inner['meta'], trunc = trunc)

def p_gereral_row(p):
    '''
    general_row : row
                | object_id
    '''
    p[0] = p[1]

def p_row_update(p):
    '''
    row_update : general_row
               | '+' general_row
               | '-' general_row
    '''
    if len(p) == 3:
        p[0] = morkast.RowUpdate(p[2], p[1])
    else:
        p[0] = p[1]

def p_row_move(p):
    '''
    row_update : object_id '!' HEX
    '''
    p[0] = morkast.RowMove(p[1], int(p[3], 16))

def p_row_inner_cell(p):
    '''
    row_inner :
              | row_inner cell
    '''
    if len(p) == 1:
        p[0] = { 'cells': [], 'meta': [] }
    else:
        p[1]['cells'].append(p[2])
        p[0] = p[1]

def p_row_inner_meta(p):
    '''
    row_inner : row_inner meta_row
    '''
    p[1]['meta'].append(p[2])
    p[0] = p[1]

def p_meta_row(p):
    '''
    meta_row : '[' cell_list ']'
    '''
    p[0] = morkast.MetaRow(p[2])

def p_table(p):
    '''
    table : '{' object_id table_inner '}'
          | '{' '-' object_id table_inner '}'
    '''
    if len(p) == 6:
        trunc = True
        objid, inner = p[3:5]
    else:
        trunc = False
        objid, inner = p[2:4]

    p[0] = morkast.Table(objid, inner['rows'], inner['meta'], trunc)

def p_table_inner_row(p):
    '''
    table_inner :
                | table_inner row_update
    '''
    if len(p) == 1:
        p[0] = { 'rows': [], 'meta': [] }
    else:
        p[1]['rows'].append(p[2])
        p[0] = p[1]

def p_table_inner_meta(p):
    '''
    table_inner : table_inner meta_table
    '''
    p[1]['meta'].append(p[2])
    p[0] = p[1]

# Rows appear in metatables. I don't know why.
def p_meta_table(p):
    '''
    meta_table : '{' cell_row_list '}'
    '''
    p[0] = morkast.MetaTable(p[2]['cells'], p[2]['rows'])

def p_cell_row_list_cell(p):
    '''
    cell_row_list :
                  | cell_row_list cell
    '''
    if len(p) == 1:
        p[0] = { 'cells': [], 'rows': [] }
    else:
        p[1]['cells'].append(p[2])
        p[0] = p[1]

def p_cell_row_list_row(p):
    '''
    cell_row_list : cell_row_list general_row
    '''
    p[1]['rows'].append(p[2])
    p[0] = p[1]

def p_cell_list(p):
    '''
    cell_list :
              | cell_list cell
    '''
    if len(p) == 1:
        p[0] = []
    else:
        p[1].append(p[2])
        p[0] = p[1]

def p_cell(p):
    '''
    cell : LPAREN cell_column cell_value RPAREN
         | '-' LPAREN cell_column cell_value RPAREN
    '''
    if len(p) == 6:
        p[0] = morkast.Cell(p[3], p[4], cut = True)
    else:
        p[0] = morkast.Cell(p[2], p[3])

def p_cell_column(p):
    '''
    cell_column : NAME
                | object_reference
    '''
    p[0] = p[1]

def p_cell_value(p):
    '''
    cell_value : VALUE
               | object_reference
    '''
    p[0] = p[1]

def p_object_reference(p):
    '''
    object_reference : CARET HEX
                     | CARET HEX COLON NAME
    '''
    if len(p) == 3:
        obj = morkast.ObjectId(p[2])
    else:
        obj = morkast.ObjectId(p[2], p[4])

    p[0] = morkast.ObjectRef(obj)

def p_object_id(p):
    '''
    object_id : HEX
              | HEX COLON NAME
    '''
    if len(p) == 2:
        p[0] = morkast.ObjectId(p[1])
    else:
        p[0] = morkast.ObjectId(p[1], p[3])

def p_object_id_refscope(p):
    '''
    object_id : HEX COLON object_reference
    '''
    p[0] = morkast.ObjectId(p[1], p[3])

def p_error(tok):
    if tok is None:
        print 'Syntax error at end of input'
    else:
        print 'Syntax error at token', tok
        # Try to continue
        yacc.errok()

yacc.yacc()

def parse(data):
    return yacc.parse(data)

def parse_file(f):
    if isinstance(f, basestring):
        f = open(f)

    return parse(f.read())
