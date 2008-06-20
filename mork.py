import re
import sys

class MorkParser(object):
    def __init__(self, data):
        self._data = data
        self._index = 0

        self._parse()

    def _parse(self):
        # Remove the initial comment (and any space)
        self._eatWhiteSpace()
        self._eatComment()

        while self._index < len(self._data):
            self._eatWhiteSpace()
            self._parseNext()

    def _parseNext(self):
        pass

    def _match(self, regex):
        m = regex.match(self._data, self._index)
        if m:
            self._index = m.end()
        return m

    _space = re.compile(r'\s+')
    def _eatWhiteSpace(self):
        self._match(self._space)

    _comment = re.compile(r'//.*\n')
    def _eatComment(self):
        self._match(self._comment)
