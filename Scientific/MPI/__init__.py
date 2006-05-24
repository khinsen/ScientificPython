from core import *
from core import _C_API

import sys
if sys.modules.has_key('pythondoc'):
    import core, types
    from core import __doc__
    for name in dir(core):
        object = getattr(core, name)
        if type(object) == types.ClassType:
            setattr(object, '__module__', 'Scientific.MPI')
        elif type(object) == types.FunctionType:
            object.func_globals['__name__'] = 'Scientific.MPI'
    del core
    del types
del sys
