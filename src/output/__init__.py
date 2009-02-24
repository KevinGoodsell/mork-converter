import sys
import os

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

def iterFilters():
    filterDir = os.path.dirname(os.path.abspath(__file__))
    modulesSeen = set()

    for name in os.listdir(filterDir):
        filtName = os.path.splitext(name)[0]
        # Skip already seen files
        if filtName in modulesSeen:
            continue
        modulesSeen.add(filtName)

        try:
            module = getFilter(filtName)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            continue

        yield (filtName, module)
