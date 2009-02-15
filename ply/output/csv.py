import output.util as util

usage = [
    util.Argument('outname', 'Name to use for output directory (or file, if'
        ' singlefile is used)'),
    util.Argument('singlefile', 'Output no a single file instead of one file'
        ' per table', util.convertBool),
    util.Argument('overwrite', 'Overwrite existing file(s)', util.convertBool),
]

def output(db, args):
    args = util.convertArgs(usage, args)
    return output_helper(db, **args)

def output_helper(db, outname='csvout', singlefile=False, overwrite=False):
    pass
