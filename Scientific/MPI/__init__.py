from core import *
from core import _C_API

"""
Python interface to the Message Passing Interface (MPI)

This module contains a Python interface to the Message Passing
Interface (MPI), and standardized library for message-passing parallel
computing. Please read an introduction to MPI before using this
module; some terms in the documentation do not make much sense unless
you understand the principles of MPI.

This module contains an object, 'world', which represents the
default communicator in MPI. This communicator can be used directly
for sending and receiving data, or other communicators can be
derived from it.

A number of global constants are also defined (L{max}, L{min}, L{prod},
L{sum}, L{land}, L{lor}, L{lxor}, L{band}, L{bor}, L{bxor}, L{maxloc}),
and L{minloc}). They are used to specify the desired operator in calls to
the 'reduce' and 'allreduce' methods of the communicator objects.

@undocumented: core*
"""

import sys
if sys.modules.has_key('epydoc'):
    import core, types
    core_name = core.__name__
    from core import __doc__
    for name in dir(core):
        object = getattr(core, name)
        if type(object) == types.ClassType:
            setattr(object, '__module__', 'Scientific.MPI')
        elif type(object) == types.FunctionType:
            object.func_globals['__name__'] = 'Scientific.MPI'
    core.__name__ = core_name
    del core
    del core_name
    del object
    del name
    del types
del sys
