# High-level parallelization classes
#
# Written by Konrad Hinsen <khinsen@cea.fr>
# last revision: 2005-9-26
#

"""This module contains high-level parallelization constructs
based on the Bulk Synchronous Parallel (BSP) model.

Parallelization requires a low-level communications library, which can
be either BSPlib or MPI. Programs must be run with the bsppython or
mpipython executables in order to use several processors. When run
with a standard Python interpreter, only one processor is available.

A warning about object identity: when a communication operation
transmits a Python object to the same processor, the object in the
return list can either be the sent object or a copy of it. Application
programs thus should not make any assumptions about received objects
being different from sent objects.
"""

_undocumented = 1

import RemoteObjects
from Scientific import N
import cPickle, operator, sys, types

try:
    virtual_bsp_machine = sys.virtual_bsp_machine
    bsplib = None
    world = None
except AttributeError:
    virtual_bsp_machine = None
    try:
        import Scientific_bsplib
        bsplib = Scientific_bsplib
        world = None
    except ImportError:
        bsplib = None
        from Scientific.MPI import world
        try:
            if world.__class__.__name__ == "DummyCommunicator":
                world = None
        except AttributeError:
            pass
        if world is not None:
            world = world.duplicate()

#
# Number of processors
#
if virtual_bsp_machine is not None:
    numberOfProcessors = virtual_bsp_machine.numberOfProcessors()
    processorID = virtual_bsp_machine.currentPid()
elif bsplib is not None:
    numberOfProcessors = bsplib.numberOfProcessors
    processorID = bsplib.processorID
elif world is not None:
    numberOfProcessors = world.size
    processorID = world.rank
else:
    numberOfProcessors = 1
    processorID = 0

#
# Low-level communication: send and receive arbitrary objects via MPI
#
if world is not None:

    _type_tags = {N.Int8: 3, N.Int16: 4, N.Int32: 5,
                  N.UnsignedInt8: 6,
                  N.Float16: 7, N.Float: 8,
                  N.Complex32: 9, N.Complex64: 10}
    _type_tags_i = {}
    for key, value in _type_tags.items():
        _type_tags_i[value] = key

    _debug_flag = 0
    def _debug(flag):
        global _debug_flag
        _debug_flag = flag

    def _send(obj, destinations):
        requests = []
        if type(obj) is N.arraytype:
            send_data = obj
            tag = _type_tags.get(send_data.typecode(), 2)
            if _debug_flag:
                print world.rank, "sending array (type %s, shape %s) to %s" \
                      % (send_data.typecode(), str(obj.shape), \
                         str(destinations))
                sys.stdout.flush()
            if tag == 2:
                send_data = cPickle.dumps(send_data, 1)
            else:
                shape = N.array(obj.shape)
                for pid in destinations:
                    requests.append(world.nonblockingSend(shape, pid, tag))
                tag = 1
        else:
            if _debug_flag:
                print world.rank, "sending non-array object to", destinations
                sys.stdout.flush()
            send_data = cPickle.dumps(obj, 1)
            tag = 2
        if _debug_flag:
            print world.rank, "sending data (%d) to" % tag, destinations
            sys.stdout.flush()
        for pid in destinations:
            requests.append(world.nonblockingSend(send_data, pid, tag))
        return requests

    def _wait(requests):
        if _debug_flag:
            print world.rank, "waiting for %d requests" % len(requests)
            sys.stdout.flush()
        for r in requests:
            r.wait()
        if _debug_flag:
            print world.rank, "finished waiting"
            sys.stdout.flush()

    def _receive(source, tag):
        if tag == 2:
            if _debug_flag:
                print world.rank, "receiving non-array object from", source
                sys.stdout.flush()
            data = cPickle.loads(world.receiveString(source, tag)[0])
            return data
        else:
            if _debug_flag:
                print world.rank, "receiving array shape from", source
                sys.stdout.flush()
            typecode = _type_tags_i.get(tag, None)
            if typecode is None:
                raise ValueError("Invalid tag " + `tag`)
            shape = world.receive(N.Int, source, tag)[0]
            if _debug_flag:
                print world.rank, "shape: ", shape
                print world.rank, "receiving array data from", source
                sys.stdout.flush()
            data = world.receive(typecode, source, 1)[0]
            data.shape = tuple(shape)
            if _debug_flag:
                print world.rank, "done receiving"
                sys.stdout.flush()
            return data

#
# BSP communication level: exchange messages and synchronize
#
if virtual_bsp_machine is not None:

    put = virtual_bsp_machine.put
    send = virtual_bsp_machine.send
    sync = virtual_bsp_machine.sync

elif bsplib is not None:

    def put(obj, pid_list):
        if type(obj) is not N.arraytype:
            obj = cPickle.dumps(obj, 1)
        for pid in pid_list:
            bsplib.send(obj, pid)
            
    def send(messages):
        for pid, data in messages:
            put(data, [pid])

    def sync():
        bsplib.sync()
        messages = []
        while 1:
            data = bsplib.receive()
            if data is None: break
            if type(data) is N.arraytype:
                messages.append(data)
            else:
                messages.append(cPickle.loads(data))
        return messages

elif world is not None:

    _requests = []

    def put(obj, pid_list):
        global _requests
        if len(pid_list) > 0:
            _requests = _requests + _send(obj, pid_list)

    def send(messages):
        global _requests
        for pid, data in messages:
            _requests = _requests + _send(data, [pid])
        
    def sync():
        global _requests
        for pid in range(numberOfProcessors):
            _requests.append(world.nonblockingSend('', pid, 0))
        messages = []
        pcount = 0
        while pcount < numberOfProcessors:
            test = world.nonblockingProbe()
            if test is None: continue
            source, tag = test
            if tag == 0:
                pcount = pcount + 1
                world.receiveString(source, tag)
            else:
                messages.append(_receive(source, tag))
        _wait(_requests)
        _requests = []
        world.barrier()
        return messages

else:

    _messages = []

    def put(obj, pid_list):
        global _messages
        for pid in pid_list:
            if pid == 0:
                _messages.append(obj)
            else:
                raise ValueError("invalid pid")

    def send(messages):
        for pid, data in messages:
            put(data, [pid])

    def sync():
        global _messages
        messages = _messages
        _messages = []
        return messages

#
# Higher-level communications layer. This code takes care of the handling
# of special objects and of special transfer needs of particular objects.
#

def retrieveMessages():
    messages = sync()
    filtered_messages = []
    for m in messages:
        if isinstance(m, RemoteObjects.TransferToken):
            RemoteObjects.remote_object_manager.handleTransfer(m)
        else:
            filtered_messages.append(m)
    return filtered_messages

#
# The dictionary _wrappers stores the global class corresponding
# to each local class. Whenever a global object is constructed
# from a local one, the appropriate class is looked up here.
# If no wrapper class is found, ParValue is used.
#
_wrappers = {}

def global_object(local_object):
    try:
        klass = local_object.__class__
    except AttributeError:
        return ParValue(local_object)
    wrapper = _wrappers.get(klass, ParValue)
    return wrapper(local_object)

#
# ParValue is the base class for all standard distributed-data classes.
#
class ParValue(object):

    """Global data

    ParValue instances are created internally, but are not meant to be
    created directly by application programs. Use the subclasses instead.

    ParValue objects (and those of subclasses) implement the standard
    arithmetic and comparison operations. They also support attribute
    requests which are passed on to the local values; the return
    values are ParValue objects. ParValue objects can also be called
    if their local values are callable.
    """

    def __init__(self, value, valid=1):
        self.value = value
        self.valid = valid

    is_parvalue = 1

    def __len__(self):
        return len(self.value)

    def __repr__(self):
        if self.valid:
            return "%s[%d](%s)" % (self.__class__.__name__, processorID,
                                   repr(self.value))
        else:
            return "<%s object (no valid data)>" % self.__class__.__name__
    __str__ = __repr__

    def __call__(self, *args, **kwargs):
        params = []
        valid = self.valid
        for a in args:
            p, v = _getValue(a)
            valid = valid and v
            params.append(p)
        kw = {}
        for key, data in kwargs.items():
            p, v = _getValue(data)
            kw[key] = p
            valid = valid and v
        if valid:
            return global_object(apply(self.value, params, kw))
        else:
            return ParValue(None, 0)

    def put(self, pid_list):
        """Sends the local data to all processors in |pid_list| (a global
        object). Returns a ParValue object whose local value is a list of
        all the data received from other processors. The order of the
        data in that list is not defined.
        """
        if self.valid:
            if not pid_list.valid:
                raise ValueError("Invalid processor ID list")
            put(self.value, pid_list.value)
        return ParValue(retrieveMessages())

    def get(self, pid_list):
        """Requests the local data from all processors in |pid_list| (a global
        object). Returns a ParValue object whose local value is a list of
        all the data received from other processors. The order of the
        data in that list is not defined.
        """
        if not pid_list.valid:
            raise ValueError("Invalid processor ID list")
        put(processorID, pid_list.value)
        destinations = sync()
        if self.valid:
            put(self.value, destinations)
        return ParValue(retrieveMessages())

    def broadcast(self, from_pid=0):
        """Transmits the local data on processor |from_pid| to all
        processors. Returns a ParValue object.
        """
        if processorID == from_pid:
            if self.valid:
                put(self.value, range(numberOfProcessors))
            else:
                raise ValueError("Broadcast for invalid data")
        return ParValue(retrieveMessages()[0])

    def fullExchange(self):
        """Transmits the local data of each processor to all other
        processors. Returns a ParValue object.
        """
        if self.valid:
            put(self.value, range(numberOfProcessors))
        return ParValue(retrieveMessages())

    def reduce(self, operator, zero):
        """Performs a reduction with |operator| over the local values
        of all processors using |zero| as initial value. The result
        is a ParValue object with the reduction result on processor 0
        and |zero| on all other processors.
        """
        if self.valid:
            put(self.value, [0])
        return ParValue(reduce(operator, retrieveMessages(), zero),
                        processorID == 0)

    def accumulate(self, operator, zero):
        """Performs an accumulation with |operator| over the local values
        of all processors using |zero| as initial value. The result
        is a ParValue object whose local value on each processor is the
        reduction of the values from all processors with lower or equal
        number.
        """
        if self.valid:
            data = self
        else:
            data = ParValue(zero)
        data = data.get(ParValue(range(processorID+1)))
        return ParValue(reduce(operator, data.value, zero))

    def __nonzero__(self):
        if not self.valid:
            raise ValueError("invalid local value")
        return operator.truth(self.value)

    def alltrue(self):
        """Returns 1 (local value) if the local values on all
        processors are true.
        """
        if self.valid:
            put(operator.truth(self.value), [0])
        all = sync()
        if processorID == 0:
            combined = reduce(operator.and_, all, 1)
            put(combined, range(numberOfProcessors))
        return sync()[0]

    def anytrue(self):
        """Returns 1 (local value) if at least one of the local values on all
        processors is true.
        """
        if self.valid:
            put(operator.truth(self.value), [0])
        all = sync()
        if processorID == 0:
            combined = reduce(operator.or_, all, 0)
            put(combined, range(numberOfProcessors))
        return sync()[0]

    def __eq__(self, other):
        if self.valid and other.valid:
            return ParValue(self.value == other.value)
        else:
            return ParValue(None, 0)

    def __ne__(self, other):
        if self.valid and other.valid:
            return ParValue(self.value != other.value)
        else:
            return ParValue(None, 0)

    def __lt__(self, other):
        if self.valid and other.valid:
            return ParValue(self.value < other.value)
        else:
            return ParValue(None, 0)

    def __le__(self, other):
        if self.valid and other.valid:
            return ParValue(self.value <= other.value)
        else:
            return ParValue(None, 0)

    def __gt__(self, other):
        if self.valid and other.valid:
            return ParValue(self.value > other.value)
        else:
            return ParValue(None, 0)

    def __ge__(self, other):
        if self.valid and other.valid:
            return ParValue(self.value >= other.value)
        else:
            return ParValue(None, 0)

    def __neg__(self):
        if self.valid:
            return ParValue(-self.value)
        else:
            return ParValue(None, 0)
            
    def __add__(self, other):
        if self.valid and other.valid:
            return ParValue(self.value + other.value)
        else:
            return ParValue(None, 0)

    def __sub__(self, other):
        if self.valid and other.valid:
            return ParValue(self.value - other.value)
        else:
            return ParValue(None, 0)

    def __mul__(self, other):
        if self.valid and other.valid:
            return ParValue(self.value * other.value)
        else:
            return ParValue(None, 0)

    def __div__(self, other):
        if self.valid and other.valid:
            return ParValue(self.value / other.value)
        else:
            return ParValue(None, 0)

    def __mod__(self, other):
        if self.valid and other.valid:
            return ParValue(self.value % other.value)
        else:
            return ParValue(None, 0)

    def __divmod__(self, other):
        if self.valid and other.valid:
            div, mod = divmod(self.value, other.value)
            return ParValue(div), ParValue(mod)
        else:
            return ParValue(None, 0), ParValue(None, 0)

    def __pow__(self, other):
        if self.valid and other.valid:
            return ParValue(self.value ** other.value)
        else:
            return ParValue(None, 0)

    def __getitem__(self, item):
        if not self.valid:
            return ParValue(None, 0)
        if hasattr(item, 'is_parindex'):
            if not item.valid:
                return ParValue(None, 0)
            if item.skip == 0:
                try:
                    return global_object(self.value[item.start])
                except IndexError:
                    return ParValue(None, 0)
            if item.skip == 1:
                if item.stop is None:
                    return global_object(self.value[item.start:])
                else:
                    return global_object(self.value[item.start:item.stop])
            else:
                return global_object(self.value[item.start:item.stop:item.skip])
        elif hasattr(item, 'is_parvalue'):
            if item.valid:
                return global_object(self.value[item.value])
            else:
                return ParValue(None, 0)
        else:
            return global_object(self.value[item])

    def __getattr__(self, attr):
        if attr == 'valid' or attr == '__coerce__':
            raise AttributeError
        if not self.valid:
            return ParValue(None, 0)
        return global_object(getattr(self.value, attr))

    def getattr(self, attr):
        if not self.valid:
            return ParValue(None, 0)
        return global_object(getattr(self.value, attr.value))

    def map(self, function):
        if not self.valid:
            return ParValue(None, 0)
        if hasattr(function, 'is_parvalue'):
            function = function.value
        return ParValue(map(function, self.value))

#
# Extract local value and validity flag from a ParValue
def _getValue(x):
    if isinstance(x, ParValue):
        return x.value, x.valid
    else:
        return x, 1

#
# ParConstant represents an identical value on each processor.
#
class ParConstant(ParValue):

    """Global constant

    A subclass of ParValue.

    Constructor: ParConstant(|value|)

    Arguments:

    |value| -- any local or global object
    """

    def __init__(self, value):
        if hasattr(value, 'is_parvalue'):
            self.value = value.value
        else:
            self.value = value
        self.valid = 1

#
# ParData generates the local values as a function of processor id
# and number of processors.
#
class ParData(ParValue):

    """Global data

    A subclass of ParValue

    Constructor: ParData(|function|)

    Arguments:

    |function| -- a function of two arguments (processor number and
                  number of processors in the machine) whose return
                  value becomes the local value of the global object.
    """

    def __init__(self, function):
        self.value = function(processorID, numberOfProcessors)
        self.valid = 1

#
# ParSequence objects distribute a sequence over the processors
#
class ParSequence(ParValue):

    """Global distributed sequence

    A subclass of ParValue.

    Constructor: ParSequence(|full_sequence|)

    Arguments:

    |full_sequence| -- any indexable and sliceable Python sequence

    The local value of a ParSequence object is a slice of |full_sequence|,
    which is constructed such that the concatenation of the local values
    of all processors equals |full_sequence|.
    """

    def __init__(self, full_sequence):
        if hasattr(full_sequence, 'is_parvalue'):
            if not full_sequence.valid:
                self.valid = 0
                self.value = None
                return
            full_sequence = full_sequence.value
        self.length = len(full_sequence)
        chunk = (self.length+numberOfProcessors-1)/numberOfProcessors
        self.first = min(processorID*chunk, self.length)
        self.last = min(self.first+chunk, self.length)
        self.value = full_sequence[self.first:self.last]
        self.valid = 1

    def totalLength(self):
        return ParValue(self.length)

    def __getitem__(self, item):
        if not self.valid:
            return ParValue(None, 0)
        if hasattr(item, 'is_parindex'):
            if not item.valid:
                return ParValue(None, 0)
            if item.skip == 0:
                try:
                    return global_object(self.value[item.start-self.first])
                except IndexError:
                    return ParValue(None, 0)
            if item.skip == 1:
                if item.stop is None:
                    return global_object(self.value[item.start-self.first:])
                else:
                    return global_object(self.value[item.start-self.first
                                                    :item.stop-self.first])
            else:
                return global_object(self.value[item.start-self.first
                                                :item.stop-self.first
                                                :item.skip])
        else:
            return global_object(self.value[item-self.first])

#
# ParMessages serves to send exchange arbitray data between processors.
#
class ParMessages(ParValue):

    """Global message list

    A subclass of ParValue.

    Constructor: ParMessage(|messages|)

    Arguments:

    |messages| -- a global object whose local value is a list of
                  (pid, data) pairs.
    """

    def __init__(self, messages):
        if hasattr(messages, 'is_parvalue'):
            messages = messages.value
        self.value = messages
        self.valid = 1

    def processorIds(self):
        """Returns a ParValue object whose local value is a list of
        all processor Ids referenced in a message.
        """
        return ParValue(map(lambda x: x[0], self.value))

    def data(self):
        """Returns a ParValue object whose local value is a list of
        all data items in the messages.
        """
        return ParValue(map(lambda x: x[1], self.value))

    def exchange(self):
        """Sends all the messages and returns a ParValue object
        containing the received messages.
        """
        if self.valid:
            send(self.value)
        return ParMessages(retrieveMessages())

#
# ParTuple combines several ParValues to speed up communication.
#
class ParTuple(ParValue):

    """Global data tuple

    A subclass of ParValue.

    Constructor: ParTuple(|x1|, |x2|, ...)

    Arguments:

    |x1|, |x2|, ... -- global objects

    ParTuple objects are used to speed up communication when many data
    items need to be sent to the same processors. The construct
    a, b, c = ParTuple(a, b, c).put(pids) is logically equivalent to
    a = a.put(pids); b = b.put(pids); c = c.put(pids) but more efficient.
    """

    def __init__(self, *args):
        self.value = map(lambda pv: pv.value, args)
        self.valid = reduce(operator.and_, map(lambda pv: pv.valid, args))

    def __getitem__(self, item):
        if self.valid:
            return ParValue(self.value[item])
        else:
            return ParValue(None, 0)

    def __len__(self):
        return len(self.value)

#
# ParAccumulator serves to accumulate data in a parallelized loop.
#
class ParAccumulator(ParValue):

    """Global accumulator

    A subclass of ParValue.

    Constructor: ParAccumulator(|operator|, |zero|)

    Arguments:

    |operator| -- a local function taking two arguments and returning
                  one argument of the same type.

    |zero| -- an initial value for reduction.

    ParAccumulator objects are used to perform iterative reduction
    operations in loops. The initial local value is |zero|, which is
    modified by subsequent calls to the method addValue.
    """

    def __init__(self, operator, zero):
        self.operator = operator
        self.zero = zero
        self.value = zero
        self.valid = 1

    def addValue(self, value):
        """Replaces the internal value of the accumulator by
        internal_value = operator(internal_value, value).
        """
        if value.valid:
            self.value = self.operator(self.value, value.value)

    def calculateTotal(self):
        """Performs a reduction operation over the current local
        values on all processors. Returns a ParValue object.
        """
        return self.reduce(self.operator, self.zero)

#
# ParFunction represents a set of identical functions
# on all processors.
#
class ParFunction(ParValue):

    """Global function

    A subclass of ParValue.

    Constructor: ParFunction(|local_function|)

    Arguments:

    |local_function| -- a local function

    Global functions are called with global object arguments.
    The local values of these arguments are then passed to the local
    function, and the result is returned in a ParValue object.
    """

    def __init__(self, local_function):
        self.value = local_function
        self.valid = 1

    def __repr__(self):
        return "ParFunction[%d](%s)" % (processorID, self.value.__name__)

#
# ParRootFunction represents a function with different code for processor
# zero and all the others. By default, the other processors do nothing
# and return None.
#
class ParRootFunction(ParFunction):

    """Asymmetric global function

    Constructor: ParRootFunction(|root_function|, |other_function|=None)

    Arguments:

    |root_function| -- the local function for processor 0

    |other_function| -- the local function for all other processors. The
                        default is a function that returns None.

    Global functions are called with global object arguments.
    The local values of these arguments are then passed to the local
    function, and the result is returned in a ParValue object.

    A ParRootFunction differs from a ParFunction in that it uses a different
    local function for processor 0 than for the other processors.
    ParRootFunction objects are commonly used for I/O operations.
    """

    def __init__(self, local_function, other_function=None):
        if processorID == 0:
            self.value = local_function
        else:
            if other_function is None:
                def other_function(*args, **kwargs):
                    return ParValue(None)
            self.value = other_function
        self.local_instance = None
        self.valid = 1

#
# ParIndex objects are returned by ParIndexIterator.
#
class ParIndex(object):

    def __init__(self, index, valid=1):
        if hasattr(index, 'is_parvalue'):
            self.valid = index.valid
            if self.valid:
                self.start = index.value
            else:
                self.start = 0
        elif hasattr(index, 'is_parindex'):
            self.valid = index.valid
            self.start = index.start
        else:
            self.start = index
            self.valid = valid
        self.stop = self.start+1
        self.skip = 0

    def __repr__(self):
        return "ParIndex[%d](%d)" % (processorID, self.start)

    is_parindex = 1

class ParSlice(ParIndex):

    def __init__(self, start=0, stop=None, skip=1, valid=1):
        self.start = start
        self.stop = stop
        self.skip = skip
        self.valid = valid

    def __repr__(self):
        return "ParSlice[%d](%d, %d, %d)" % (processorID, self.start,
                                             self.stop, self.skip)


#
# Direct iteration over distributed sequences.
#
class ParIterator(object):

    """Parallel iterator

    Constructor: ParIterator(|global_sequence|)

    Arguments:

    |global_sequence| -- a global object representing a distributed
                         sequence

    A ParIterator is used to loop element by element over a distributed
    sequence. At each iteration, the returned item (a global object)
    contains different elements of the distributed sequence.
    """

    def __init__(self, sequence):
        self.sequence = sequence.value
        self.n = len(sequence.value)
        self.max_n = ParValue(self.n).reduce(max, 0).broadcast().value

    def __getitem__(self, item):
        if item >= self.max_n:
            raise IndexError
        if item >= self.n:
            return ParValue(None, 0)
        return global_object(self.sequence[item])

#
# Index iteration over distributed sequences.
#
class ParIndexIterator(object):

    """Parallel index iterator

    Constructor: ParIndexIterator(|global_sequence|)

    Arguments:

    |global_sequence| -- a global object representing a distributed
                         sequence

    A ParIndexIterator is used to loop index by index over one or more
    distributed sequences. At each iteration, the returned item (a
    global index object) contains indices of different elements of the
    distributed sequence(s). The index objects can be used to index
    any ParValue object whose local value is a sequence object.
    """

    def __init__(self, sequence):
        self.n = len(sequence.value)
        self.max_n = ParValue(self.n).reduce(max, 0).broadcast().value

    def __getitem__(self, item):
        if item >= self.max_n:
            raise IndexError
        if item >= self.n:
            return ParIndex(0, 0)
        return ParIndex(item)

#
# Distribution class. This effectively turns all methods
# into ParMethods and all other attributes inte ParValues.
#
class ParClass(object):

    """Global class

    Constructor: ParClass(|local_class|)

    Arguments:

    |local_class| -- a local class

    Global classes are needed to construct global objects that
    have more functionalities than offered by the ParValue class hierarchy.
    When an instance of a global class is generated, each processor
    generates an instance of |local_class| that becomes the local value
    of the new global object. Attribute requests and method calls
    are passed through to the local objects and the results are
    assembled into global objects (ParValue or ParFunction). The arguments
    to methods of a global class must be global objects, the local class
    methods are then called with the corresponding local values.

    The local objects are initialized via the special method
    __parinit__ instead of the usual __init__. This method is called
    with two special arguments (processor number and total number of
    processors) followed by the local values of the arguments to the
    global object initialization call.

    The local classes must inherit from the base class ParBase (see below),
    which also provides  communication routines.
    """

    def __init__(self, local_class):
        self.local_class = local_class
        self.attributes = {}
        self.collectAttributes(local_class, self.attributes)
        try:
            del self.attributes['__init__']
        except KeyError:
            pass

        class _Wrapper(object):
            def __init__(self, local_instance):
                self.value = local_instance
                self.valid = 1
            is_parvalue = 1
            def __repr__(self):
                if self.attributes.has_key('__repr__'):
                    return "ParClass{%s}[%d](%s)" \
                                  % (self.local_class.__name__, processorID,
                                     repr(self.value))
                else:
                    return "ParClass{%s}[%d] instance: %s" \
                                  % (self.local_class.__name__, processorID,
                                     repr(self.value))
            def __getattr__(self, name):
                try:
                    return global_object(self.value.__dict__[name])
                except KeyError:
                    pass
                try:
                    value = self.attributes[name]
                except KeyError:
                    value = getattr(self.value, name)
                if isinstance(value, types.MethodType):
                    return ParMethod(value, self.value)
                else:
                    return global_object(value)
            def __getitem__(self, item):
                item, valid = _getValue(item)
                if valid:
                    return global_object(self.value[item])
                else:
                    return ParValue(None, 0)
            def __call__(self, *args, **kwargs):
                params = []
                valid = True
                for a in args:
                    p, v = _getValue(a)
                    valid = valid and v
                    params.append(p)
                kw = {}
                for key, data in kwargs.items():
                    p, v = _getValue(data)
                    kw[key] = p
                    valid = valid and v
                if valid:
                    return global_object(self.value(*params, **kw))
                else:
                    return ParValue(None, 0)


        self.wrapper = _Wrapper
        self.wrapper.__module__ = local_class.__module__
        self.wrapper.__name__ = "ParClass(%s)" % local_class.__name__
        self.wrapper.attributes = self.attributes
        self.wrapper.local_class = local_class
        _wrappers[local_class] = self.wrapper

    def collectAttributes1(self, klass, attrib_dict):
        for key in klass.__dict__.keys():
            if key not in ['__doc__', '__module__', '__name__', '__bases__']:
                if not attrib_dict.has_key(key):
                    attrib_dict[key] = getattr(klass, key)

    def collectAttributes(self, klass, attrib_dict):
        self.collectAttributes1(klass, attrib_dict)
        for base_class in klass.__bases__:
            self.collectAttributes(base_class, attrib_dict)
            
    def __call__(self, *args, **kwargs):
        args = (processorID, numberOfProcessors) + args
        local_instance = _DummyClass()
        local_instance.__class__ = self.local_class
        local_instance.__parinit__(*args, **kwargs)
        return self.wrapper(local_instance)

# Dummy class
class _DummyClass(object):
    pass

#
# Special 'invalid' object. It is passed to methods in distributed
# object classes and accepted as a return value.
#
class _ParInvalid(object):
    pass

def is_invalid(obj):
    return isinstance(obj, _ParInvalid)

ParInvalid = _ParInvalid()
_wrappers[_ParInvalid] = lambda x: ParValue(None, 0)

#
# ParMethod represents a set of identical methods
# on all processors.
#
class ParMethod(ParFunction):

    def __init__(self, local_function, local_instance):
        self.value = local_function
        self.local_instance = local_instance
        self.valid = 1

    def __repr__(self):
        return "ParMethod[%d](%s)" % (processorID, self.value.__name__)

    def __call__(self, *args, **kwargs):
        params = [self.local_instance]
        for a in args:
            if hasattr(a, 'is_parvalue'):
                if a.valid:
                    params.append(a.value)
                else:
                    params.append(ParInvalid)
            else:
                params.append(a)
        kw = {}
        for key, data in kwargs.items():
            if hasattr(data, 'is_parvalue'):
                if data.valid:
                    kw[key] = data.value
                else:
                    kw[key] = ParInvalid
            else:
                kw[key] = data
        ret = apply(self.value, params, kw)
        return global_object(ret)

#
# Abstract base class that provides communication for ParClasses.
#
class ParBase(object):

    """Distributed data base class

    Local classes that are to be used in global classes
    must inherit from this class.
    """

    is_parclass = 1

    def put(self, data, pid_list):
        """Send |data| to all processors in |pid_list|. Returns the list
        of received objects.
        """
        put(data, pid_list)
        return retrieveMessages()

    def get(self, data, pid_list):
        """Requests the local values of |data| of all processors in |pid_list|.
        Returns the list of received objects.
        """
        put(processorID, pid_list)
        destinations = sync()
        put(data, destinations)
        return retrieveMessages()

    def broadcast(self, data, from_pid=0):
        """Sends the local value of |data| on processor |from_pid| to
        all processors. Returns the received object.
        """
        if processorID == from_pid:
            put(data, range(numberOfProcessors))
        return retrieveMessages()[0]

    def exchangeMessages(self, message_list):
        """Sends the (pid, data) messages in |message_list| to the destination
        processors. Returns the list of incoming data.
        """
        send(message_list)
        return retrieveMessages()

