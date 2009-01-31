

class MorkAst(object):
    @staticmethod
    def indent(s):
        return '  ' + s.replace('\n', '\n  ')

    @staticmethod
    def formatList(items):
        return '\n'.join(str(item) for item in items)

    @staticmethod
    def indentList(name, items):
        if items:
            text = MorkAst.formatList(items)
            return '%s:\n%s' % (name, MorkAst.indent(text))
        else:
            return '%s: (empty)' % name

class Database(MorkAst):
    def __init__(self, items):
        self.items = items

    def __repr__(self):
        return repr(self.items)

    def __str__(self):
        return self.formatList(self.items)

class Group(MorkAst):
    def __init__(self, groupid, items, commit):
        self.groupid = groupid
        self.items = items
        self.commit = commit

    def __repr__(self):
        return 'Group(%r, %r, %r)' % (self.groupid, self.items, self.commit)

    def __str__(self):
        members = 'commit: %r\n%s' % (self.commit,
            self.indentList('items', self.items))
        return 'Group %s:\n%s' % (self.groupid, self.indent(members))

class Dict(MorkAst):
    def __init__(self, cells=None, meta=None):
        if cells is None:
            cells = []
        if meta is None:
            meta = []

        self.cells = cells
        self.meta = meta

    def __repr__(self):
        return 'Dict(%r, %r)' % (self.cells, self.meta)

    def __str__(self):
        members = '%s\n%s' % (self.indentList('meta', self.meta),
            self.indentList('cells', self.cells))
        return 'Dict:\n%s' % self.indent(members)

class MetaDict(Dict):
    def __init__(self, cells=None):
        Dict.__init__(self, cells)

    def __repr__(self):
        return 'MetaDict(%r)' % self.cells

    def __str__(self):
        return self.indentList('MetaDict', self.cells)

class Row(MorkAst):
    def __init__(self, rowid, cells=None, meta=None, cut=False):
        if cells is None:
            cells = []
        if meta is None:
            meta = []

        self.rowid = rowid
        self.cells = cells
        self.meta = meta
        self.cut = cut

    def __repr__(self):
        return 'Row(%r, %r, %r, %r)' % (self.rowid, self.cells, self.meta,
            self.cut)

    def __str__(self):
        members = 'cut: %s\n%s\n%s' % (self.cut,
            self.indentList('meta', self.meta),
            self.indentList('cells', self.cells))
        return 'Row %s:\n%s' % (self.rowid, self.indent(members))

class MetaRow(Row):
    def __init__(self, cells=None):
        Row.__init__(self, None, cells)

    def __repr__(self):
        return 'MetaRow(%r)' % self.cells

    def __str__(self):
        return 'MetaRow:\n%s' % self.indentList('cells', self.cells)

class Table(MorkAst):
    def __init__(self, tableid, rows=None, meta=None, cut=False):
        if rows is None:
            rows = []
        if meta is None:
            meta = []

        self.tableid = tableid
        self.rows = rows
        self.meta = meta
        self.cut = cut

    def __repr__(self):
        return 'Table(%r, %r, %r, %r)' % (self.tableid, self.rows, self.meta,
            self.cut)

    def __str__(self):
        members = 'cut: %s\n%s\n%s' % (self.cut,
            self.indentList('meta', self.meta),
            self.indentList('rows', self.rows))
        return 'Table %s:\n%s' % (self.tableid, self.indent(members))

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

    def __repr__(self):
        return 'MetaTable(%r, %r)' % (self.cells, self.other)

    def __str__(self):
        members = '%s\n%s' % (self.indentList('cells', self.cells),
            self.indentList('other', self.other))
        return 'MetaTable:\n%s' % self.indent(members)

class Cell(MorkAst):
    def __init__(self, column, value):
        self.column = column
        self.value = value

    def __repr__(self):
        return 'Cell(%r, %r)' % (self.column, self.value)

    def __str__(self):
        return 'Cell: %s = %s' % (self.column, self.value)

class ObjectId(MorkAst):
    def __init__(self, objectid, scope=None):
        self.objectid = objectid
        self.scope = scope

    def __repr__(self):
        if self.scope is None:
            return 'ObjectId(%r)' % self.objectid
        else:
            return 'ObjectId(%r, %r)' % (self.objectid, self.scope)

    def __str__(self):
        if self.scope is None:
            return self.objectid
        else:
            return '%s:%s' % (self.objectid, self.scope)

class ObjectRef(MorkAst):
    def __init__(self, obj):
        self.obj = obj

    def __repr__(self):
        return 'ObjectRef(%r)' % self.obj

    def __str__(self):
        return '^%s' % self.obj
