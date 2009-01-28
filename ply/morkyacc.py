import re
import ply.yacc as yacc

from morklex import tokens
import morkast

def p_mork_db(p):
    'mork : MAGIC item_group_list'
    p[0] = p[2]

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
    # XXX This is missing updates
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

    commit = p[1].find('~abort~') == -1

    p[0] = morkast.Group(m.group('id'), p[2], commit)

def p_dict(p):
    '''
    dict : '<' dict_inner '>'
    '''
    p[0] = p[2]

def p_dict_inner_cell(p):
    '''
    dict_inner :
               | dict_inner cell
    '''
    if len(p) == 1:
        p[0] = morkast.Dict()
    else:
        p[1].cells.append(p[2])
        p[0] = p[1]

def p_dict_inner_meta(p):
    '''
    dict_inner : dict_inner meta_dict
    '''
    p[1].meta.append(p[2])
    p[0] = p[1]

def p_meta_dict(p):
    '''
    meta_dict : '<' cell_list '>'
    '''
    p[0] = morkast.MetaDict(p[2])

def p_row(p):
    '''
    row : '[' object_id row_inner ']'
    '''
    p[0] = morkast.Row(p[2], p[3]['cells'], p[3]['meta'])

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
    '''
    p[0] = morkast.Table(p[2], p[3]['rows'], p[3]['meta'])

def p_table_inner_row(p):
    '''
    table_inner :
                | table_inner row
                | table_inner object_id
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

def p_meta_table(p):
    '''
    meta_table : '{' cell_objid_list '}'
    '''
    p[0] = morkast.MetaTable(p[2]['cells'], p[2]['other'])

# XXX object IDs in meta tables seems to violate the spec but matches my sample
# files.
def p_cell_objid_list_cell(p):
    '''
    cell_objid_list :
                    | cell_objid_list cell
    '''
    if len(p) == 1:
        p[0] = { 'cells': [], 'other': [] }
    else:
        p[1]['cells'].append(p[2])
        p[0] = p[1]

def p_cell_objid_list_objid(p):
    '''
    cell_objid_list : cell_objid_list object_id
    '''
    p[1]['other'].append(p[2])
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
    '''
    p[0] = morkast.Cell(p[2], p[3])

def p_cell_column(p):
    '''
    cell_column : LITERAL
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
    object_reference : OBJREF
                     | OBJREF ':' LITERAL
    '''
    if len(p) == 2:
        obj = morkast.ObjectId(p[1][1:])
    else:
        obj = morkast.ObjectId(p[1][1:], p[3])

    p[0] = morkast.ObjectRef(obj)

def p_object_id(p):
    '''
    object_id : OBJID
              | OBJID ':' LITERAL
    '''
    if len(p) == 2:
        p[0] = morkast.ObjectId(p[1])
    else:
        p[0] = morkast.ObjectId(p[1], p[3])

def p_object_id_refscope(p):
    '''
    object_id : OBJID ':' OBJREF
    '''
    scopeObj = morkast.ObjectId(p[3][1:])
    scope = morkast.ObjectRef(scopeObj)
    p[0] = morkast.ObjectId(p[1], scope)

yacc.yacc()

# DEBUG

data = open('../Drafts-1.msf').read()
tree = yacc.parse(data)
