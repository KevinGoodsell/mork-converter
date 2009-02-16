import sys
import getopt

import output.csv

def usage(msg=None):
    if msg:
        print >> sys.stderr, msg
    print >> sys.stderr, ('usage: %s [--tokens|--syntax|--format=<outformat>]'
        ' [--help] [file ...]' % sys.argv[0])
    # XXX need help for output formats

class BadFilter(StandardError):
    pass

def getFilter(nameAndArgs):
    pieces = nameAndArgs.split(':')
    filterName = pieces[0]
    args = pieces[1:]

    argDict = {}
    for arg in args:
        pieces = arg.split('=', 1)
        argName = pieces[0]
        if len(pieces) == 1:
            argVal = ''
        else:
            argVal = pieces[1]

        argDict[argName] = argVal

    moduleName = 'output.' + filterName
    try:
        exec 'import ' + moduleName
    except ImportError:
        raise BadFilter('output filter "%s" not found' % filterName)

    return (sys.modules[moduleName], argDict)

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    try:
        (options, arguments) = getopt.getopt(args, 'h',
            ['tokens', 'syntax', 'help', 'format='])
    except getopt.GetoptError, e:
        usage(str(e))
        return 2

    tokens = False
    syntax = False
    formatGiven = False
    # XXX refactor
    filterModule = output.csv
    filterArgs = {'singlefile' : ''}
    for (opt, val) in options:
        if opt in ('-h', '--help'):
            usage()
            return 0
        elif opt == '--tokens':
            tokens = True
        elif opt == '--syntax':
            syntax = True
        elif opt == '--format':
            formatGiven = True
            try:
                (filterModule, filterArgs) = getFilter(val)
            except BadFilter, e:
                print >> sys.stderr, str(e)
                return 1

    mutualyExclusive = [opt for opt in (tokens, syntax, formatGiven) if opt]
    if len(mutualyExclusive) > 1:
        usage('choose one (or zero) of --tokens, --syntax, or --format')
        return 2

    if len(arguments) == 0:
        arguments = ['-']

    for arg in arguments:
        if arg == '-':
            f = sys.stdin
        else:
            f = open(arg)

        # XXX Refactor this
        if tokens:
            import morklex
            morklex.printTokens(f)
        else:
            import morkyacc
            tree = morkyacc.parseFile(f)
            if syntax:
                print tree
            else:
                # XXX Not much to do with DBs right now
                import morkdb
                db = morkdb.MorkDatabase.fromAst(tree)
                filterModule.output(db, filterArgs)


if __name__ == '__main__':
    sys.exit(main())
