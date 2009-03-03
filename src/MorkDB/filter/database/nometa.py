# Copyright (c) 2009 Kevin Goodsell
import MorkDB.filter.util as util

_MORK_DATABASE_FILTER = True

description = 'Strip meta-tables from the database'
usage = []

def filter(db, args):
    args = util.convertArgs(usage, args)
    _filterHelper(db, **args)

def _filterHelper(db):
    db.metaTables.clear()
