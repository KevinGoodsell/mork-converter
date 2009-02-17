import sys

class BadFilter(StandardError):
    pass

def getFilter(name):
    moduleName = 'output.' + name
    try:
        exec 'import ' + moduleName
    except ImportError:
        raise BadFilter('output filter not found: %s' % name)

    module = sys.modules[moduleName]
    if not hasattr(module, '_MORK_OUTPUT_FILTER'):
        raise BadFilter('not a valid output filter: %s' % name)

    return module
