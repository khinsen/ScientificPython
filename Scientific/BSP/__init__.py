from core import numberOfProcessors, processorID, ParValue, ParConstant, \
     ParData, ParSequence, ParMessages, ParTuple, ParAccumulator, \
     ParFunction, ParRootFunction, ParIndex, ParIterator, \
     ParIndexIterator, ParClass, ParBase, ParInvalid, is_invalid

import sys
if sys.modules.has_key('pythondoc'):
    import core, types
    from core import __doc__
    for name in dir(core):
        object = getattr(core, name)
        if type(object) == types.ClassType:
            setattr(object, '__module__', 'Scientific.BSP')
        elif type(object) == types.FunctionType:
            object.func_globals['__name__'] = 'Scientific.BSP'
    del types
del sys
