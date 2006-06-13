done = False

try:
    from Scientific import use_numeric
    from Numeric import *
    del use_numeric
    done = True
    def int_sum(a, axis=0):
        return add.reduce(a, axis)

except ImportError:
    pass

if not done:
    try:
        from Scientific import use_numpy
        from numpy import *
        del use_numpy
        done = True
        def int_sum(a, axis=0):
            return add.reduce(a, axis)

    except ImportError:
        pass

if not done:
    try:
        from Scientific import use_numarray
        from numarray import *
        del use_numarray
        done = True
        def int_sum(a, axis=0):
            return add.reduce(a, axis, type=Int)

    except ImportError:
        pass

del done
