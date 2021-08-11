'''
Copyright 2009, 2010 Kevin Goodsell

morkdb.py -- classes for representing data from a Mork database, and functions
for building them from Abstract Syntax Trees.
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

from __future__ import absolute_import
import warnings
import re

from . import morkast

class MorkDict(dict):
    def __init__(self):
        dict.__init__(self)

        # I'm not really sure this initialization is right. It seems
        # unnecessary in test files, but should also be harmless.
        for i in range(0x80):
            col = '%X' % i
            value = chr(i)
            self[col] = value

    @staticmethod
    def from_ast(ast, db):
        assert isinstance(ast, morkast.Dict)

        # Create a MorkDict from ast.aliases
        aliases = MorkDict()
        for alias in ast.aliases:
            aliases[alias.key] = db._unescape(alias.value)

        # Find the namespace (if any) in ast.meta
        namespace = 'a'
        assert len(ast.meta) <= 1, 'multiple meta-dicts'
        if ast.meta:
            for cell in ast.meta[0].cells:
                if cell.column == 'a':
                    namespace = cell.value
                else:
                    warnings.warn('ignoring some meta-dict cells')

        existing = db.dicts.get(namespace)
        if existing is None:
            db.dicts[namespace] = aliases
        else:
            existing.update(aliases)

class _MorkStore(dict):
    def __init__(self):
        dict.__init__(self) # { ('namespace', 'id'): object } }

    def items(self):
        for ((namespace, oid), obj) in dict.items(self):
            yield (namespace, oid, obj)

class MorkTableStore(_MorkStore):
    pass

class MorkRowStore(_MorkStore):
    pass

class MorkRowList(list): # [ ('namespace', 'id', MorkRow) ]
    def clear(self):
        del self[:]

    def append(self, namespace, rowid, row):
        list.append(self, (namespace, rowid, row))

    def index(self, namespace, rowid):
        for (i, (ns, rid, row)) in enumerate(self):
            if ns == namespace and rid == rowid:
                return i

        raise ValueError('row (%s, %s) not found in table' % (namespace,
                                                              rowid))

    def move_row(self, namespace, rowid, new_pos):
        pos = self.index(namespace, rowid)

        if new_pos >= len(self):
            warning.warn('during row move, new_pos is outside of table range')
            new_pos = len(self) - 1

        item = self[pos]
        if pos < new_pos:
            self[pos:new_pos+1] = self[pos+1:new_pos+1] + [item]
        else:
            self[new_pos:pos+1] = [item] + self[new_pos:pos]

    def remove_row(self, namespace, rowid):
        i = self.index(namespace, rowid)
        del self[i]

class MorkTable(MorkRowList):
    def __init__(self):
        MorkRowList.__init__(self)

    def column_names(self):
        columns = set()
        for (namespace, rowid, row) in self:
            columns.update(row.column_names())

        return columns

    @staticmethod
    def from_ast(ast, db):
        assert isinstance(ast, morkast.Table)

        # Get id and namespace
        (oid, namespace) = db._dissectId(ast.tableid)
        assert namespace is not None, 'no namespace found for table'

        # Start with an empty table if trunc or if there's no table currently
        self = db.tables.get((namespace, oid))
        if self is None:
            self = MorkTable()
        elif ast.trunc:
            self.clear()

        db._readRows(ast.rows, namespace, self)

        assert len(ast.meta) <= 1, 'multiple meta-tables'
        if ast.meta:
            MorkMetaTable.from_ast(ast.meta[0], db, namespace, oid)

        # Insert into table store
        db.tables[namespace, oid] = self

        return self

class MorkMetaTable(object):
    # A meta-table is pretty much a set of cells, which makes it a lot like a
    # row. It can also contain rows -- my guess is that there can only be one
    # row, and that the row cells are added to the meta-table cells. Parts of
    # this implementation reflect this view.
    def __init__(self):
        self.cells = {}
        self.rows = MorkRowList()

    def column_names(self):
        columns = set(self.cells.keys())
        for (ns, rowid, row) in self.rows:
            columns.update(row.keys())

        return columns

    def __getitem__(self, column):
        # I doubt there's more than one row per meta-table
        for (ns, rowid, row) in self.rows:
            if column in row:
                return row[column]

        if column in self.cells:
            return self.cells[column]
        else:
            raise KeyError(repr(column))

    @staticmethod
    def from_ast(ast, db, table_namespace, tableid):
        assert isinstance(ast, morkast.MetaTable)

        self = MorkMetaTable()
        db._readRows(ast.rows, table_namespace, self.rows)

        for cell in ast.cells:
            (column, value) = db._inflateCell(cell)
            self.cells[column] = value

        db.meta_tables[table_namespace, tableid] = self

        return self

class MorkRow(dict):
    def __init__(self):
        dict.__init__(self)

    def column_names(self):
        return list(self.keys())

    @staticmethod
    def from_ast(ast, db, default_namespace=None):
        assert isinstance(ast, morkast.Row)

        # Get id and namespace
        (oid, namespace) = db._dissectId(ast.rowid, default_namespace)
        assert namespace is not None, 'no namespace found for row'

        # Start with an empty row if trunc or if there's no row currently
        self = db.rows.get((namespace, oid))
        if self is None:
            self = MorkRow()
        elif ast.trunc:
            self.clear()

        for cell in ast.cells:
            (column, value) = db._inflateCell(cell)
            if cell.cut:
                self.pop(column, None)
            else:
                self[column] = value

        if ast.meta:
            warnings.warn('ignoring meta-row')

        # insert into row store
        db.rows[namespace, oid] = self

        return self

def process_mork_group_ast(ast, db):
    assert isinstance(ast, morkast.Group)

    if not ast.commit:
        return

    for item in ast.items:
        db.build_item(item)

class MorkDatabase(object):
    def __init__(self):
        self.dicts = {} # { 'namespace': MorkDict }
        self.tables = MorkTableStore()
        self.meta_tables = MorkTableStore()
        self.rows = MorkRowStore()

        self.dicts['a'] = MorkDict()
        self.dicts['c'] = MorkDict()

    # **** A bunch of utility methods ****

    def _dictDeref(self, objref, default_namespace='c'):
        assert isinstance(objref, morkast.ObjectRef)

        (oid, namespace) = self._dissectId(objref.obj, default_namespace)

        return self.dicts[namespace][oid]

    def _dissectId(self, oid, default_namespace=None):
        '''
        Return ('objectid', 'namespace') or ('objectid', None) if the
        namespace cannot be determined.
        '''
        assert isinstance(oid, morkast.ObjectId)

        namespace = oid.scope
        if isinstance(namespace, morkast.ObjectRef):
            namespace = self._dictDeref(namespace)
        elif namespace is None:
            namespace = default_namespace

        return (oid.objectid, namespace)

    _unescapeMap = {
        r'\)': ')', r'\\': '\\', r'\$': '$',  # basic escapes
        '\\\r\n': '', '\\\n': '', '\\\r': '', # line continuation
    }
    def _translateEscape(self, match):
        text = match.group()
        if text.startswith('$'):
            return chr(int(text[1:], 16))

        return self._unescapeMap[text]

    _escape = re.compile(r'\$[0-9a-fA-F]{2}|\\\r\n|\\.', re.DOTALL)
    def _unescape(self, value):
        return self._escape.sub(self._translateEscape, value)

    def _inflateCell(self, cell):
        column = cell.column
        if isinstance(column, morkast.ObjectRef):
            column = self._dictDeref(column)

        value = cell.value
        if isinstance(value, morkast.ObjectRef):
            value = self._dictDeref(value, 'a')
        else:
            value = self._unescape(value)

        return (column, value)

    def _readRows(self, rows, table_namespace, row_list):
        for row in rows:
            # Each row could be morkast.Row, morkast.RowUpdate,
            # morkast.RowMove, or morkast.ObjectId
            if isinstance(row, morkast.RowMove):
                (rowid, row_namespace) = self._dissectId(row.rowid,
                                                        table_namespace)

                row_list.move_row(row_namespace, rowid, row.position)
                continue

            update = '+'
            if isinstance(row, morkast.RowUpdate):
                update = row.method
                row = row.obj

            if isinstance(row, morkast.ObjectId):
                row_id_ast = row
            elif isinstance(row, morkast.Row):
                row_id_ast = row.rowid
                MorkRow.from_ast(row, self, table_namespace)
            else:
                raise Exception('Bad row type: %s' % type(row))

            (rowid, row_namespace) = self._dissectId(row_id_ast, table_namespace)

            if update == '+':
                row_list.append(row_namespace, rowid,
                               self.rows[row_namespace, rowid])
            elif update == '-':
                row_list.remove_row(row_namespace, rowid)
            else:
                raise NotImplementedError('Unhandled row update type: %r' %
                                          update)

    # **** Database builder ****

    _builder = {
        morkast.Dict:  MorkDict.from_ast,
        morkast.Row:   MorkRow.from_ast,
        morkast.Table: MorkTable.from_ast,
        morkast.Group: process_mork_group_ast,
    }

    def build_item(self, ast):
        builder = self._builder.get(ast.__class__)
        assert builder is not None, ("unknown item with type '%s'" %
                                     ast.__class__)

        builder(ast, self)

    @staticmethod
    def from_ast(ast):
        assert isinstance(ast, morkast.Database)

        self = MorkDatabase()

        for item in ast.items:
            self.build_item(item)

        return self
