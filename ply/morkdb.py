
class MorkDatabase(object):
    def __init__(self):
        self.dicts = {}
        self.tables = {}
        self.rows = {}
        self.groups = {}

        # default scopes for columns and literals
        c = {}
        a = {}
        # initialization for dicts
        # XXX I'm not really sure this initialization is rigt.
        for i in xrange(0x80):
            col = '%X' % i
            value = chr(i)
            c[col] = value
            a[col] = value

        self.dicts['c'] = c
        self.dicts['a'] = a
