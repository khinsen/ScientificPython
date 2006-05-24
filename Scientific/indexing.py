# A nicer way to build up index tuples for arrays.
#
# You can do all this with slice() plus a few special objects,
# but there's a lot to remember. This version is simpler because
# it uses the standard array indexing syntax.
#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 1999-7-23
#

"""This module provides a convenient method for constructing
array indices algorithmically. It provides one importable object,
'index_expression'.

For any index combination, including slicing and axis insertion,
'a[indices]' is the same as 'a[index_expression[indices]]' for any
array 'a'. However, 'index_expression[indices]' can be used anywhere
in Python code and returns a tuple of indexing objects that can be
used in the construction of complex index expressions.

Sole restriction: Slices must be specified in the double-colon
form, i.e. a[::] is allowed, whereas a[:] is not.
"""

class _index_expression_class:

    import sys
    maxint = sys.maxint

    def __init__(self):
        pass

    def __getitem__(self, item):
        if type(item) != type(()):
            return (item,)
        else:
            return item

    def __len__(self):
        return self.maxint

    def __getslice__(self, start, stop):
        if stop == self.maxint:
            stop = None
        return self[start:stop:None]

index_expression = _index_expression_class()
