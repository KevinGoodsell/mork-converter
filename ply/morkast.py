

class MorkAst(object):
    def __str__(self):
        raise NotImplementedError

class Group(MorkAst):
    def __init__(self, groupid, items, commit):
        self.groupid = groupid
        self.items = items
        self.commit = commit

class Dict(MorkAst):
    def __init__(self, cells=None, meta=None):
        if cells is None:
            cells = []
        if meta is None:
            meta = []

        self.cells = cells
        self.meta = meta

class MetaDict(Dict):
    def __init__(self, cells=None):
        Dict.__init__(self, cells)

class Row(MorkAst):
    def __init__(self, rowid, cells=None, meta=None):
        if cells is None:
            cells = []
        if meta is None:
            meta = []

        self.rowid = rowid
        self.cells = cells
        self.meta = meta

class MetaRow(Row):
    def __init__(self, cells=None):
        Row.__init__(self, None, cells)

class Table(MorkAst):
    def __init__(self, tableid, rows=None, meta=None):
        if rows is None:
            rows = []
        if meta is None:
            meta = []

        self.tableid = tableid
        self.rows = rows
        self.meta = meta

class MetaTable(MorkAst):
    # XXX 'other' is the object ids that show up in meta tables. I don't
    # know what these are for yet.
    def __init__(self, cells=None, other=None):
        if cells is None:
            cells = []
        if other is None:
            other = []

        self.cells = cells
        self.other = other

class Cell(MorkAst):
    def __init__(self, column, value):
        self.column = column
        self.value = value

class ObjectId(MorkAst):
    def __init__(self, objectid, scope = None):
        self.objectid = objectid
        self.scope = scope

class ObjectRef(MorkAst):
    def __init__(self, obj):
        self.obj = obj
