import warnings

import morkast

class _MorkDict(dict):
    def __init__(self):
        dict.__init__(self)

        # XXX I'm not really sure this initialization is right.
        for i in xrange(0x80):
            col = '%X' % i
            value = chr(i)
            self[col] = value

    @staticmethod
    def fromAst(ast, db):
        assert isinstance(ast, morkast.Dict)

        # Create a _MorkDict from ast.cells
        cells = _MorkDict()
        for cell in ast.cells:
            cells[cell.column] = cell.value
            if cell.cut:
                warnings.warn("ignoring cell's 'cut' attribute")

        # Find the namespace (if any) in ast.meta
        namespace = 'a'
        assert len(ast.meta) <= 1, 'multiple meta-dicts'
        if ast.meta:
            for cell in ast.meta[0].cells:
                if cell.column == 'a':
                    namespace = cell.value
                    break

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

class _MorkTableStore(_MorkStore):
    pass

class _MorkRowStore(_MorkStore):
    pass

class _MorkTable(object):
    def __init__(self, rows=None):
        if rows is None:
            rows = []

        self._rows = set(rows)

    def columnNames(self):
        columns = set()
        for row in self._rows:
            columns.update(row.columnNames())

        return columns

    def addRow(self, row):
        self._rows.add(row)

    @staticmethod
    def fromAst(ast, db):
        assert isinstance(ast, morkast.Table)

class _MorkRow(dict):
    def __init__(self):
        dict.__init__(self)

    def columnNames(self):
        return self.keys()

    @staticmethod
    def fromAst(ast, db):
        assert isinstance(ast, morkast.Row)

class MorkDatabase(object):
    def __init__(self):
        self.dicts = {} # { 'namespace': _MorkDict }
        self.tables = _MorkTableStore()
        self.rows = _MorkRowStore()
        #self.groups = {}

        self.dicts['a'] = _MorkDict()
        self.dicts['c'] = _MorkDict()

    _builder = {
        morkast.Dict:  _MorkDict.fromAst,
        morkast.Row:   _MorkRow.fromAst,
        morkast.Table: _MorkTable.fromAst,
    }

    @staticmethod
    def fromAst(ast):
        assert isinstance(ast, morkast.Database)

        self = MorkDatabase()

        for item in ast.items:
            builder = self._builder.get(item.__class__)
            if builder is None:
                warnings.warn('skipping item of type %s' % item.__class__)
                continue

            builder(item, self)

        return self


# XXX Test
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
