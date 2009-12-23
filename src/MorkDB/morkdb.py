'''
Copyright (c) 2009 Kevin Goodsell

morkdb.py -- classes for representing data from a Mork database, and functions
for building them from Abstract Syntax Trees.
'''
import warnings
import re

import MorkDB.morkast as morkast

class MorkDict(dict):
    def __init__(self):
        dict.__init__(self)

        # I'm not really sure this initialization is right. It seems
        # unnecessary in test files, but should also be harmless.
        for i in xrange(0x80):
            col = '%X' % i
            value = chr(i)
            self[col] = value

    @staticmethod
    def fromAst(ast, db):
        assert isinstance(ast, morkast.Dict)

        # Create a MorkDict from ast.cells
        cells = MorkDict()
        for cell in ast.cells:
            cells[cell.column] = db._unescape(cell.value)
            # 'cut' doesn't seem to have any meaning in a dict
            assert not cell.cut, "found a 'cut' cell in a dict"

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
            db.dicts[namespace] = cells
        else:
            existing.update(cells)

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

class MorkRowList(object):
    def __init__(self):
        self.rows = [] # [ ('namespace', 'id', MorkRow) ]

    def clear(self):
        del self.rows[:]

    def append(self, namespace, rowid, row):
        self.rows.append((namespace, rowid, row))

    def index(self, namespace, rowid):
        for (i, (ns, rid, row)) in enumerate(self.rows):
            if ns == namespace and rid == rowid:
                return i

        raise ValueError('row (%s, %s) not found in table' % (namespace,
                                                              rowid))

    def moveRow(self, namespace, rowid, newPos):
        pos = self.index(namespace, rowid)

        if newPos >= len(self.rows):
            warning.warn('during row move, newPos is outside of table range')
            newPos = len(self.rows) - 1

        item = self.rows[pos]
        if pos < newPos:
            self.rows[pos:newPos+1] = self.rows[pos+1:newPos+1] + [item]
        else:
            self.rows[newPos:pos+1] = [item] + self.rows[newPos:pos]

    def removeRow(self, namespace, rowid):
        i = self.index(namespace, rowid)
        del self.rows[i]

    def __iter__(self):
        return iter(self.rows)

class MorkTable(MorkRowList):
    def __init__(self):
        MorkRowList.__init__(self)

    def columnNames(self):
        columns = set()
        for (namespace, rowid, row) in self.rows:
            columns.update(row.columnNames())

        return columns

    @staticmethod
    def fromAst(ast, db):
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
            MorkMetaTable.fromAst(ast.meta[0], db, namespace, oid)

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

    def columnNames(self):
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
    def fromAst(ast, db, tableNamespace, tableId):
        assert isinstance(ast, morkast.MetaTable)

        self = MorkMetaTable()
        db._readRows(ast.rows, tableNamespace, self.rows)

        for cell in ast.cells:
            (column, value) = db._inflateCell(cell)
            self.cells[column] = value

        db.metaTables[tableNamespace, tableId] = self

        return self

class MorkRow(dict):
    def __init__(self):
        dict.__init__(self)

    def columnNames(self):
        return self.keys()

    @staticmethod
    def fromAst(ast, db, defaultNamespace=None):
        assert isinstance(ast, morkast.Row)

        # Get id and namespace
        (oid, namespace) = db._dissectId(ast.rowid, defaultNamespace)
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

def processMorkGroupAst(ast, db):
    assert isinstance(ast, morkast.Group)

    if not ast.commit:
        return

    for item in ast.items:
        db.buildItem(item)

class MorkDatabase(object):
    def __init__(self):
        self.dicts = {} # { 'namespace': MorkDict }
        self.tables = MorkTableStore()
        self.metaTables = MorkTableStore()
        self.rows = MorkRowStore()

        self.dicts['a'] = MorkDict()
        self.dicts['c'] = MorkDict()

    # **** A bunch of utility methods ****

    def _dictDeref(self, objref, defaultNamespace='c'):
        assert isinstance(objref, morkast.ObjectRef)

        (oid, namespace) = self._dissectId(objref.obj, defaultNamespace)

        return self.dicts[namespace][oid]

    def _dissectId(self, oid, defaultNamespace=None):
        '''
        Return ('objectId', 'namespace') or ('objectId', None) if the
        namespace cannot be determined.
        '''
        assert isinstance(oid, morkast.ObjectId)

        namespace = oid.scope
        if isinstance(namespace, morkast.ObjectRef):
            namespace = self._dictDeref(namespace)
        elif namespace is None:
            namespace = defaultNamespace

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

    def _readRows(self, rows, tableNamespace, rowList):
        for row in rows:
            # Each row could be morkast.Row, morkast.RowUpdate,
            # morkast.RowMove, or morkast.ObjectId
            if isinstance(row, morkast.RowMove):
                (rowId, rowNamespace) = self._dissectId(row.rowid,
                                                        tableNamespace)

                rowList.moveRow(rowNamespace, rowId, row.position)
                continue

            update = '+'
            if isinstance(row, morkast.RowUpdate):
                update = row.method
                row = row.obj

            if isinstance(row, morkast.ObjectId):
                rowIdAst = row
            elif isinstance(row, morkast.Row):
                rowIdAst = row.rowid
                MorkRow.fromAst(row, self, tableNamespace)
            else:
                raise StandardError('Bad row type: %s' % type(row))

            (rowId, rowNamespace) = self._dissectId(rowIdAst, tableNamespace)

            if update == '+':
                rowList.append(rowNamespace, rowId,
                               self.rows[rowNamespace, rowId])
            elif update == '-':
                rowList.removeRow(rowNamespace, rowId)
            else:
                raise NotImplementedError('Unhandled row update type: %r' %
                                          update)

    # **** Database builder ****

    _builder = {
        morkast.Dict:  MorkDict.fromAst,
        morkast.Row:   MorkRow.fromAst,
        morkast.Table: MorkTable.fromAst,
        morkast.Group: processMorkGroupAst,
    }

    def buildItem(self, ast):
        builder = self._builder.get(ast.__class__)
        assert builder is not None, ("unknown item with type '%s'" %
                                     ast.__class__)

        builder(ast, self)

    @staticmethod
    def fromAst(ast):
        assert isinstance(ast, morkast.Database)

        self = MorkDatabase()

        for item in ast.items:
            self.buildItem(item)

        return self
