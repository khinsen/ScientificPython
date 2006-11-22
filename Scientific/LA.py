done = False

try:
    from Scientific import use_numeric
    from LinearAlgebra import *
    del use_numeric
    done = True
except ImportError:
    pass

if not done:
    try:
        from Scientific import use_numpy
        from numpy.oldnumeric.linear_algebra import *
        del use_numpy
        done = True
    except ImportError:
        pass

if not done:
    try:
        from Scientific import use_numarray
        from numarray.linear_algebra import *
        del use_numarray
        done = True
    except ImportError:
        pass

del done
