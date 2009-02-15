
class ArgumentError(ValueError):
    pass

def convertArgs(usage, args):
    converters = dict((arg.name, arg.converter) for arg in usage)
    result = {}

    try:
        for (argName, value) in args.items():
            converter = converters[argName]
            result[argName] = converter(value)
    except KeyError:
        raise ArgumentError('unrecognized argument: %s' % argName)

    return result

def convertBool(text):
    lower = text.lower()
    if lower in ('', 'true', 'yes'):
        return True
    elif lower in ('false', 'no'):
        return False
    else:
        raise ArgumentError("value can't be interpreted as boolean: %s" % text)

class Argument(object):
    def __init__(self, name, description, converter=None):
        self.name = name
        self.description = description
        self.converter = converter

    def convert(self, text):
        if self.converter is None:
            return text
        else:
            return self.converter(text)

    # simulate a 2-item sequence
    def __getitem__(self, index):
        if index == 0:
            return self.name
        elif index == 1:
            return self.description
        else:
            raise IndexError
