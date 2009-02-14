import sys
import getopt

def usage(msg=None):
    if msg:
        print msg
    print 'usage: %s [--tokens|--syntax] [--help] <files>' % sys.argv[0]

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    try:
        (options, arguments) = getopt.getopt(args, 'h',
            ['tokens', 'syntax', 'help'])
    except getopt.GetoptError, e:
        usage(str(e))
        return 2

    tokens = False
    syntax = False
    for (opt, val) in options:
        if opt in ('-h', '--help'):
            usage()
            return 0
        elif opt == '--tokens':
            tokens = True
        elif opt == '--syntax':
            syntax = True

    if tokens and syntax:
        usage('--syntax and --tokens are mutually exclusive')
        return 2

    if len(arguments) == 0:
        arguments = ['-']

    for arg in arguments:
        if arg == '-':
            f = sys.stdin
        else:
            f = open(arg)

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

                import pdb
                pdb.set_trace()


if __name__ == '__main__':
    sys.exit(main())
