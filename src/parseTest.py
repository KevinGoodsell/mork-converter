import sys

import morkyacc

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    if len(args) == 0:
        args = ['-']

    for arg in args:
        if arg == '-':
            tree = morkyacc.parseFile(sys.stdin)
        else:
            tree = morkyacc.parseFile(arg)

        print tree

if __name__ == '__main__':
    sys.exit(main())
