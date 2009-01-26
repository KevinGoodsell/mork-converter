import ply.yacc as yacc

from morklex import tokens

def p_mork_db(p):
    'mork : MAGIC item_group_list'
    pass

def p_item_or_group(p):
    '''
    item_group : item
               | group
    '''
    pass

def p_item_group_list(p):
    '''
    item_group_list :
                    | item_group_list item_group
    '''
    pass

def p_item(p):
    '''
    item : dict
         | row
         | table
    '''
    # XXX This is missing updates
    pass

def p_item_list(p):
    '''
    item_list :
              | item_list item
    '''
    pass

def p_group(p):
    '''
    group : GROUPSTART item_list GROUPCOMMIT
          | GROUPSTART item_list GROUPABORT
    '''
    pass

def p_dict(p):
    '''
    dict : '<' dict_inner '>'
    '''
    pass

def p_dict_inner(p):
    '''
    dict_inner :
               | dict_inner cell
               | dict_inner meta_dict
    '''
    pass

def p_meta_dict(p):
    '''
    meta_dict : '<' cell_list '>'
    '''

def p_row(p):
    '''
    row : '[' object_id row_inner ']'
    '''
    pass

def p_row_inner(p):
    '''
    row_inner :
              | row_inner cell
              | row_inner meta_row
    '''
    pass

def p_meta_row(p):
    '''
    meta_row : '[' cell_list ']'
    '''
    pass

def p_table(p):
    '''
    table : '{' object_id table_inner '}'
    '''
    pass

def p_table_inner(p):
    '''
    table_inner :
                | table_inner row
                | table_inner object_id
                | table_inner meta_table
    '''
    pass

def p_meta_table(p):
    '''
    meta_table : '{' cell_objid_list '}'
    '''
    pass

# XXX object IDs in meta tables seems to violate the spec but matches my sample
# file. It may be that my sample file is broken.
def p_cell_objid_list(p):
    '''
    cell_objid_list :
                    | cell_objid_list cell
                    | cell_objid_list object_id
    '''
    pass

def p_cell_list(p):
    '''
    cell_list :
              | cell_list cell
    '''
    pass

def p_cell(p):
    '''
    cell : LPAREN cell_column cell_value RPAREN
    '''
    pass

def p_cell_column(p):
    '''
    cell_column : LITERAL
                | object_reference
    '''
    pass

def p_cell_value(p):
    '''
    cell_value : VALUE
               | object_reference
    '''
    pass

def p_object_reference(p):
    '''
    object_reference : OBJREF
                     | OBJREF ':' LITERAL
    '''
    pass

def p_object_id(p):
    '''
    object_id : OBJID
              | OBJID ':' LITERAL
              | OBJID ':' OBJREF
    '''
    pass

yacc.yacc()

# DEBUG

data = open('../Drafts-1.msf').read()
