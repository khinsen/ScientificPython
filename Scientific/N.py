_undocumented = 1

try:
    from Scientific import use_numpy
    from numpy import *
    del use_numpy

    def int_sum(a, axis=0):
        return add.reduce(a, axis)

except ImportError:
    pass

try:
    from Scientific import use_numarray
    from numarray import *
    del use_numarray

    def int_sum(a, axis=0):
        return add.reduce(a, axis, type=Int)

except ImportError:
    pass

try:
    from Scientific import use_numeric
    from Numeric import *
    del use_numeric

    def int_sum(a, axis=0):
        return add.reduce(a, axis)

except ImportError:
    pass
