try:
    from Scientific import use_numarray
    from numarray.linear_algebra import *
    del use_numarray
except ImportError:
    pass

try:
    from Scientific import use_numeric
    from LinearAlgebra import *
    del use_numeric
except ImportError:
    pass
