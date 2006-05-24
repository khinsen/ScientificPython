_undocumented = 1

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

## import Scientific, os
## if os.path.exists(os.path.join(Scientific.__path__[0], 'use_numarray')):
##     from numarray import *
## else:
## del Scientific
## del os
