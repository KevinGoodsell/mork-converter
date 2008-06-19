#!/usr/bin/env python
# 
# mork2rdf.py
# 2007-09-10
#
# - derived from demork.py 0.4 
# http://off.net/~mhoye/moz/demork.py
#
# tweaked XML to RDF/XML
# added date conversion
# fixed title \0 weirdness
# warnings/errors commmented out
#
# danny.ayers@gmail.com
#
#==========================================================================
# Original "Mindy.py" copyright: Kumaran Santhanam 
#                                <kumaran@alumni.stanford.org>
#
# Subsequent butchery, demork.py: Mike Hoye 
#                                 <mhoye@off.net>
#
# Just to be crystal clear about this, Santhanam did all the heavy lifting
# (i.e. Mork-scraping) here, but apparently the strain of working on mork
# broke him; the "mindy" output was _another_ bizzare home-rolled database
# format, except this one had lots of "@" symbols in it.
#
# This is a straight-up pattern-recognition hack; I've never worked with
# Python or XML before, but not only does this spit out valid XML, if you
# drink a big glass of water while you're using it you might cure your 
# hiccups.
#
#--------------------------------------------------------------------------
# Project : demork - takes in Mork files, spits out XML
# File    : demork.py
# Version : 0.4
#--------------------------------------------------------------------------
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# Version 2 (1991) as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# For the full text of the GNU General Public License, refer to:
#   http://www.fsf.org/licenses/gpl.txt
#
# For alternative licensing terms, please contact the author.
#--------------------------------------------------------------------------
#
#  This widget has hardcoded XML entity tags in places that make it pretty
#  much specifically meant for the Mozilla history.db file. They're tagged
#  with a "#HDBXML" comment nearby, for easy searching and replacing if
#  you intend to do anything else with this and want semantics that make
#  some kind of sense. 
#
#  Version 0.1 was the first run at this, which was (as advertised)
#  only xml-ish.
#
#  Version 0.3 now includes a DTD in the XML output, and escapes the 
#  ampersands in long URLs, making for valid XML. 
#
#  0.4: replaced a regex that wasn't working properly for some people
#       with a non-regex search-and-replace that does.
#
#  0.4.1: merged a small patch provided by Mark Smith in a Bugzilla 
#         comment: https://bugzilla.mozilla.org/show_bug.cgi?id=241438#c27
#==========================================================================

#==========================================================================
# IMPORTS
#==========================================================================
import sys
import re
import getopt
import datetime # danja

from sys import stdin, stdout, stderr

#==========================================================================
# FUNCTIONS
#==========================================================================
def usage ():
    print
    print "mork2rdf - A Mork -> RDF/XML converter"
    print
    print "Based on a Mork/XML converter, (c) 2005 (c) Mike Hoye, "
    print "based on a Mork/Mindy converter, (c) 2005 Kumaran Santhanam."
    print
    print "usage: mork2rdf MORKFILE"
    print
    print "The converted output is dumped to STDOUT."
    print "A filename of '-' will take input from STDIN."
    print

#==========================================================================
# DATABASE
#==========================================================================
class Database:
    def __init__ (self):
        self.cdict  = { }
        self.adict  = { }
        self.tables = { }

class Table:
    def __init__ (self):
        self.id     = None
        self.scope  = None
        self.kind   = None
        self.rows   = { }

class Row:
    def __init__ (self):
        self.id     = None
        self.scope  = None
        self.cells  = [ ]

class Cell:
    def __init__ (self):
        self.column = None
        self.atom   = None


#==========================================================================
# UTILITIES
#==========================================================================
def invertDict (dict):
    idict = { }
    for key in dict.keys():
        idict[dict[key]] = key
    return idict

def hexcmp (x, y):
    try:
        a = int(x, 16)
        b = int(y, 16)
        if a < b:  return -1
        if a > b:  return 1
        return 0

    except:
        return cmp(x, y)


#==========================================================================
# MORK INPUT
#==========================================================================
def escapeData (match):
    return match.group() \
               .replace('\\\\n', '$0A') \
               .replace('\\)', '$29') \
               .replace('>', '$3E') \
               .replace('}', '$7D') \
               .replace(']', '$5D')

pCellText   = re.compile(r'\^(.+?)=(.*)')
pCellOid    = re.compile(r'\^(.+?)\^(.+)')
pCellEscape = re.compile(r'((?:\\[\$\0abtnvfr])|(?:\$..))')

backslash = { '\\\\' : '\\',
              '\\$'  : '$',
              '\\0'  : chr(0),
              '\\a'  : chr(7),
              '\\b'  : chr(8),
              '\\t'  : chr(9),
              '\\n'  : chr(10),
              '\\v'  : chr(11),
              '\\f'  : chr(12),
              '\\r'  : chr(13) }

def unescapeMork (match):
    s = match.group()
    if s[0] == '\\':
        return backslash[s]
    else:
        return chr(int(s[1:], 16))

def decodeMorkValue (value):
    global pCellEscape
    return pCellEscape.sub(unescapeMork, value)

def addToDict (dict, cells):
    for cell in cells:
        eq  = cell.find('=')
        key = cell[1:eq]
        val = cell[eq+1:-1]
        dict[key] = decodeMorkValue(val)

def getRowIdScope (rowid, cdict):
    idx = rowid.find(':')
    if idx > 0:
        return (rowid[:idx], cdict[rowid[idx+2:]])
    else:
        return (rowid, None)
        
def delRow (db, table, rowid):
    (rowid, scope) = getRowIdScope(rowid, db.cdict)
    if scope:
        rowkey = rowid + "/" + scope
    else:
        rowkey = rowid + "/" + table.scope

    if table.rows.has_key(rowkey):
        del table.rows[rowkey]

def addRow (db, table, rowid, cells):
    global pCellText
    global pCellOid

    row = Row()
    (row.id, row.scope) = getRowIdScope(rowid, db.cdict)

    for cell in cells:
        obj = Cell()
        cell = cell[1:-1]

        match = pCellText.match(cell)
        if match:
            obj.column = db.cdict[match.group(1)]
            obj.atom   = decodeMorkValue(match.group(2))

        else:
            match = pCellOid.match(cell)
            if match:
                obj.column = db.cdict[match.group(1)]
                obj.atom   = db.adict[match.group(2)]

        if obj.column and obj.atom:
            row.cells.append(obj)

    if row.scope:
        rowkey = row.id + "/" + row.scope
    else:
        rowkey = row.id + "/" + table.scope

    # if table.rows.has_key(rowkey):
        # print >>stderr, "ERROR: duplicate rowid/scope %s" % rowkey
        # print >>stderr, cells

    table.rows[rowkey] = row
    
def inputMork (data):
    # Remove beginning comment
    pComment = re.compile('//.*')
    data = pComment.sub('', data, 1)

    # Remove line continuation backslashes
    pContinue = re.compile(r'(\\(?:\r|\n))')
    data = pContinue.sub('', data)

    # Remove line termination
    pLine = re.compile(r'(\n\s*)|(\r\s*)|(\r\n\s*)')
    data = pLine.sub('', data)

    # Create a database object
    db          = Database()

    # Compile the appropriate regular expressions
    pCell       = re.compile(r'(\(.+?\))')
    pSpace      = re.compile(r'\s+')
    pColumnDict = re.compile(r'<\s*<\(a=c\)>\s*(?:\/\/)?\s*(\(.+?\))\s*>')
    pAtomDict   = re.compile(r'<\s*(\(.+?\))\s*>')
    pTable      = re.compile(r'\{-?(\d+):\^(..)\s*\{\(k\^(..):c\)\(s=9u?\)\s*(.*?)\}\s*(.+?)\}')
    pRow        = re.compile(r'(-?)\s*\[(.+?)((\(.+?\)\s*)*)\]')

    pTranBegin  = re.compile(r'@\$\$\{.+?\{\@')
    pTranEnd    = re.compile(r'@\$\$\}.+?\}\@')

    # Escape all '%)>}]' characters within () cells
    data = pCell.sub(escapeData, data)

    # Iterate through the data
    index  = 0
    length = len(data)
    match  = None
    tran   = 0
    while 1:
        if match:  index += match.span()[1]
        if index >= length:  break
        sub = data[index:]

        # Skip whitespace
        match = pSpace.match(sub)
        if match:
            index += match.span()[1]
            continue

        # Parse a column dictionary
        match = pColumnDict.match(sub)
        if match:
            m = pCell.findall(match.group())
            # Remove extraneous '(f=iso-8859-1)'
            if len(m) >= 2 and m[1].find('(f=') == 0:
                m = m[1:]
            addToDict(db.cdict, m[1:])
            continue

        # Parse an atom dictionary
        match = pAtomDict.match(sub)
        if match:
            cells = pCell.findall(match.group())
            addToDict(db.adict, cells)
            continue

        # Parse a table
        match = pTable.match(sub)
        if match:
            id = match.group(1) + ':' + match.group(2)

            try:
                table = db.tables[id]

            except KeyError:
                table = Table()
                table.id    = match.group(1)
                table.scope = db.cdict[match.group(2)]
                table.kind  = db.cdict[match.group(3)]
                db.tables[id] = table

            rows = pRow.findall(match.group())
            for row in rows:
                cells = pCell.findall(row[2])
                rowid = row[1]
                if tran and rowid[0] == '-':
                    rowid = rowid[1:]
                    delRow(db, db.tables[id], rowid)

                if tran and row[0] == '-':
                    pass

                else:
                    addRow(db, db.tables[id], rowid, cells)
            continue

        # Transaction support
        match = pTranBegin.match(sub)
        if match:
            tran = 1
            continue

        match = pTranEnd.match(sub)
        if match:
            tran = 0
            continue

        match = pRow.match(sub)
        if match and tran:
            # print >>stderr, "WARNING: using table '1:^80' for dangling row: %s" % match.group()
            rowid = match.group(2)
            if rowid[0] == '-':
                rowid = rowid[1:]

# The above code is wrong for demorking purposes - empty rows
# should just be dropped.

            cells = pCell.findall(match.group(3))
            delRow(db, db.tables['1:80'], rowid)
            if row[0] != '-':
                addRow(db, db.tables['1:80'], rowid, cells)
            continue

        # Syntax error
        # print >>stderr, "ERROR: syntax error while parsing MORK file"
        # print >>stderr, "context[%d]: %s" % (index, sub[:40])
        index += 1

    # Return the database
    return db


#==========================================================================
# XML out
#
# All these "mindy" references are holdovers from this program's previous
# life. Like I said, I don't speak python, and it's not broke... -mhoye
#==========================================================================
pMindyEscape = re.compile('([\x00-\x1f\x80-\xff\\\\])')

def escapeMindy (match):
    s = match.group()
    if s == '\\': return '\\\\'
    if s == '\0': return ''
#  danja was   if s == '\0': return '\\0'
    if s == '\r': return '\\r'
    if s == '\n': return '\\n'
    return "\\x%02x" % ord(s)

def encodeMindyValue (value):
    global pMindyEscape
    return pMindyEscape.sub(escapeMindy, value)

def outputMindy (db):

#HDBXML 

    columns = db.cdict.keys()
    columns.sort(hexcmp)

    tables = db.tables.keys()
    tables.sort(hexcmp)

# BEGIN danja's nasty RDF/XML hackiness 

    print '<?xml version="1.0"?>'
    print '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"'
    print '         xmlns:foaf="http://xmlns.com/foaf/0.1/"'
    print '         xmlns:dc="http://purl.org/dc/elements/1.1/"'
    print '         xmlns:rss="http://purl.org/rss/1.0/"'
    print '         xmlns:history="http://purl.org/stuff/history/">'
    
    for table in [ db.tables[k] for k in tables ]:
        rows = table.rows.keys()
        rows.sort(hexcmp)
        for row in [ table.rows[k] for k in rows ]:
            data = dict()
            for cell in row.cells:
                data[cell.column] = re.sub('&', '&amp;', encodeMindyValue(cell.atom)) # 
            if data.has_key('URL'):
                print ' <rss:item rdf:about="%s">' % data['URL']
                if data.has_key('FirstVisitDate'):
                    isodate = datetime.date.fromtimestamp(float(data['FirstVisitDate'])/1000000).isoformat()
                    print '    <history:firstVisit>%s</history:firstVisit>' % isodate
                if data.has_key('LastVisitDate'):
                    isodate = datetime.date.fromtimestamp(float(data['LastVisitDate'])/1000000).isoformat()
                    print '    <history:lastVisit>%s</history:lastVisit>' % isodate
                if data.has_key('Referrer'):
                    print '    <history:referrer rdf:resource="%s" />' % data['Referrer']
                if data.has_key('Hostname'):
                    print '    <history:host>%s</history:host>' % data['Hostname']   
                if data.has_key('Name'):
                    print '    <dc:title>%s</dc:title>' % data['Name'] 
                if data.has_key('VisitCount'):
                    print '    <history:visits>%s</history:visits>' % data['VisitCount']                  
                print ' </rss:item>'

        print '</rdf:RDF>'
        
# END danja's nasty RDF/XML hackiness 

#==========================================================================
# MAIN PROGRAM
#==========================================================================
def main (argv=None):
    if argv is None:  argv = sys.argv

    # Parse the command line arguments
    try:
        opts, args = getopt.getopt(argv[1:], "ht")
    except:
        print "Invalid command-line argument"
        usage()
        return 1

    # Process the switches
    optTest = 0
    for o, a in opts:
        if o in ("-h"):
            usage()
            return 0
        elif o in ("-t"):
            optTest = 1

    # Read the filename
    if (len(args) != 1):
        usage()
        return 1

    filename = args[0]

    # Read the file into memory
    if (filename != '-'):
        file = open(filename, "rt")
    else:
        file = stdin

    data = file.read()
    file.close()

    # Determine the file type and process accordingly
    if (data.find('<mdb:mork') >= 0):
        db = inputMork(data)
        outputMindy(db)
    else:
        print "unknown file format: %s (I only deal with Mork, sorry)" % filename
        return 1

    # Return success
    return 0


if (__name__ == "__main__"):
    result = main()
    # Comment the next line to use the debugger
    sys.exit(result)
