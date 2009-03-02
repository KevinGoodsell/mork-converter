# Copyright (c) 2009 Kevin Goodsell
import sys
import os

class BadModule(StandardError):
    pass

class ModulePool(object):
    def __init__(self, directory, package):
        self.directory = directory
        self.package = package

    def _validateModule(self, name, module):
        raise NotImplementedError

    def iterModules(self):
        modulesSeen = set()

        for name in os.listdir(self.directory):
            moduleName = os.path.splitext(name)[0]
            # Skip already seen files
            if moduleName in modulesSeen:
                continue
            modulesSeen.add(moduleName)

            try:
                module = self.getModule(moduleName)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception:
                continue

            yield (moduleName, module)

    def getModule(self, name):
        fullName = '%s.%s' % (self.package, name)
        exec 'import ' + fullName
        module = sys.modules[fullName]
        self._validateModule(name, module)
        return module
