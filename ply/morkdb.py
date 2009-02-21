import warnings
import re

import morkast

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

class _MorkStore(object):
    def __init__(self):
        # I think this will be sort of like { (namespace, id): morkObject }
        self._store = {} # { 'namespace': { 'id': object } }

    def __getitem__(self, key):
        (namespace, oid) = key
        return self._store[namespace][oid]

    def __setitem__(self, key, value):
        (namespace, oid) = key
        self._store.setdefault(namespace, {})[oid] = value

    def get(self, key, default=None):
        result = default
        (namespace, oid) = key
        ns = self._store.get(namespace)
        if ns:
            result = ns.get(oid, default)
        return result

    def items(self):
        for (namespace, objs) in self._store.items():
            for (oid, obj) in objs.items():
                yield (namespace, oid, obj)

class MorkTableStore(_MorkStore):
    pass

class MorkRowStore(_MorkStore):
    pass

class MorkTable(object):
    def __init__(self, rows=None):
        if rows is None:
            rows = []

        self._rows = rows

    def columnNames(self):
        columns = set()
        for row in self._rows:
            columns.update(row.columnNames())

        return columns

    def addRow(self, row):
        self._rows.append(row)

    def __iter__(self):
        for row in self._rows:
            yield row

    @staticmethod
    def fromAst(ast, db):
        assert isinstance(ast, morkast.Table)

        # Get id and namespace
        (oid, namespace) = db._dissectId(ast.tableid)
        assert namespace is not None, 'no namespace found for table'

        rows = []
        for row in ast.rows:
            # row could be ObjectId or Row
            if isinstance(row, morkast.ObjectId):
                (rowId, rowNamespace) = db._dissectId(row)
                if rowNamespace is None:
                    rowNamespace = namespace
                newRow = db.rows[rowNamespace, rowId]
            else:
                # XXX This might be the place to check cut rows
                newRow = MorkRow.fromAst(row, db, namespace)

            rows.append(newRow)

        # Start with an empty table if trunc or if there's no table currently
        self = db.tables.get((namespace, oid))
        if self is None or ast.trunc:
            self = MorkTable()

        for row in rows:
            self.addRow(row)

        if ast.meta:
            warnings.warn('ignoring meta-table')

        # Insert into table store
        db.tables[namespace, oid] = self

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
        (oid, namespace) = db._dissectId(ast.rowid)
        if namespace is None:
            namespace = defaultNamespace

        assert namespace is not None, 'no namespace found for row'

        # Start with an empty row if trunc or if there's no row currently
        self = db.rows.get((namespace, oid))
        if self is None or ast.trunc:
            self = MorkRow()

        for cell in ast.cells:
            (column, value) = db._inflateCell(cell)
            if cell.cut:
                self.pop(column, None)
            else:
                self[column] = value

        if ast.cut:
            warnings.warn("ignoring row's 'cut' attribute")
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
        self.rows = MorkRowStore()

        self.dicts['a'] = MorkDict()
        self.dicts['c'] = MorkDict()

    # **** A bunch of utility methods ****

    def _dictDeref(self, objref, defaultNamespace='c'):
        assert isinstance(objref, morkast.ObjectRef)

        (oid, namespace) = self._dissectId(objref.obj)
        if namespace is None:
            namespace = defaultNamespace

        return self.dicts[namespace][oid]

    def _dissectId(self, oid):
        '''
        Return ('objectId', 'namespace') or ('objectId', None) if the
        namespace cannot be determined.
        '''
        assert isinstance(oid, morkast.ObjectId)

        namespace = oid.scope
        if isinstance(namespace, morkast.ObjectRef):
            namespace = self._dictDeref(namespace)

        return (oid.objectid, namespace)

    _unescapeMap = {
        r'\)': ')', r'\\': '\\', r'\$': '$', # basic escapes
        '\\\r\n': '', '\\\n': '',            # line continuation
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


# Test
import sys

import morkyacc

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    tree = morkyacc.parseFile(args[0])
    db = MorkDatabase.fromAst(tree)

    import pdb
    pdb.set_trace()

    return 0

if __name__ == '__main__':
    sys.exit(main())
