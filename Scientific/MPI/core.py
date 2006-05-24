# The MPI Interface is written in C; this module only contains documentation
# and imports objects from the C module.
#
# Written by Konrad Hinsen <khinsen@cea.fr>
#        and Jakob Schiotz <schiotz@fysik.dtu.dk>
# last revision: 2005-9-5
#

_undocumented = 1

"""This module contains a Python interface to the Message Passing
Interface (MPI), and standardized library for message-passing parallel
computing. Please read an introduction to MPI before using this
module; some terms in the documentation do not make much sense unless
you understand the principles of MPI.

This module contains an object, 'world', which represents the
default communicator in MPI. This communicator can be used directly
for sending and receiving data, or other communicators can be
derived from it.

A number of global constants are also defined ( 'max', 'min', 'prod',
'sum', 'land', 'lor', 'lxor', 'band', 'bor', 'bxor', 'maxloc' and
'minloc' ).  They are used to specify the desired operator in calls to
the 'reduce' and 'allreduce' methods of the communicator objects.
"""

class MPIError(EnvironmentError):
    "MPI call failed"
    pass

import sys

if sys.modules.has_key('pythondoc'):

    # Fake code just for the docstrings!

    class MPICommunicator:

        """MPI Communicator

        There is no constructor for MPI Communicator objects. The
        default communicator is given by Scientific.MPI.world, and
        other communicators can only be created by methods on an
        existing communicator object.

        A communicator object has two read-only attributes: 'rank' is
        an integer which indicates the rank of the current process in
        the communicator, and 'size' is an integer equal to the number
        of processes that participate in the communicator.
        """

        def duplicate(self):
            """Returns a new communicator object with the same properties
            as the original one."""
            pass

        def subset(self, ranks):
            """Returns a new communicator object containing a subset
            of the processes participating in the original
            one. |ranks| is a list of ranks - one for each processor
            that should belong to the new communicator.

            The method should be called by all processors and the
            return value will be the new communicator on those
            processors listed in |ranks| and |None| for the rest."""
            pass

        def send(self, data, destination, tag):
            """Sends the contents of |data| (a string or any contiguous NumPy
            array except for general object arrays) to the processor
            whose rank is |destination|, using |tag| as an identifier.
            """
            pass

        def nonblockingSend(self, data, destination, tag):
            """Sends the contents of |data| (a string or any contiguous NumPy
            array except for general object arrays) to the processor
            whose rank is |destination|, using |tag| as an identifier.
            The send is nonblocking, i.e. the call returns immediately, even
            if the destination process is not ready to receive.

            The return value is an MPIRequest object.  It is used to
            wait till the communication has actually happened.
            """
            pass
            
        def receive(self, data, source=None, tag=None):
            """Receives an array from the process with rank |source|
            with identifier |tag|. The default |source|=None means
            that messages from any process are accepted. The value
            of |data| can either be an array object, in which case it
            must be contiguous and large enough to store the
            incoming data; it must also have the correct shape.
            Alternatively, |data| can be a string specifying
            the data type (in practice, one would use Numeric.Int,
            Numeric.Float, etc.). In the latter case, a new array
            object is created to receive the data.

            The return value is a tuple containing four elements:
            the array containing the data, the source process rank
            (an integer), the message tag (an integer), and the
            number of elements that were received (an integer).
            """
            pass

        def receiveString(self, source=None, tag=None):
            """Receives a string from the process with rank |source|
            with identifier |tag|. The default |source|=None means
            that messages from any process are accepted.

            The return value is a tuple containing three elements:
            the string containing the data, the source process rank
            (an integer), and the message tag (an integer).
            """
            pass
            
        def nonblockingReceive(self, data, source=None, tag=None):
            """Receives an array from the process with rank |source|
            with identifier |tag|. The default |source|=None means
            that messages from any process are accepted. The value
            of |data| must be a contiguous array object, large enough
            to store the incoming data; it must also have the correct
            shape.  Unlike the blocking receive, the size of the array
            must be known when the call is made, as nonblocking receives
            of unknown quantities of data is not implemented.  For the
            same reason there is no nonblocking_receiveString.

            The return value is an MPIRequest object.  It is used to wait
            until the data has arrived, and will give information about
            the size, the source and the tag of the incoming message.
            """
            pass

        def nonblockingProbe(self, source=None, tag=None):
            """Checks if a message from the process with rank |source|
            and with identifier |tag| is available for immediate
            reception. The return value is 'None' if no message
            is available, otherwise a '(source, tag)' tuple is
            returned.
            """
            pass

        def broadcast(self, array, root):
            """Sends data from the process with rank |root| to all
            processes (including |root|). The parameter |array| can be
            any contiguous NumPy array except for general object arrays.
            On the process |root|, it holds the data to be sent. After
            the call, the data in |array| is the same for all processors.
            The shape and data type of |array| must be the same in
            all processes.
            """
            pass

        def share(self, send, receive):
            """Distributes data from each process to all other processes
            in the communicator. The array |send| (any contiguous NumPy
            array except for general object arrays) contains the data
            to be sent by each process, the shape and data type must be
            identical in all processes. The array |receive| must have
            the same data type as |send| and one additional dimension
            (the first one), whose length must be the number of processes
            in the communicator. After the call, the value
            of |receive[i]| is equal to the contents of the array |send|
            in process i.
            """
            pass

        def barrier(self):
            """Waits until all processes in the communicator have
            called the same method, then all processes continue."""
            pass

        def abort(self, error_code):
            """Aborts all processes associated with the communicator.
            For emergency use only. The |error_code| is passed back
            to the calling program (i.e. a shell) under most Unix
            MPI implementations."""
            pass

        def reduce(self, sendbuffer, receivebuffer, operation, root):
            """Combine data from all processes using |operation|, and
            send the data to the process identified by |root|.

            |operation| is one of the operation objects defined globally
            in the module: 'max', 'min', 'prod', 'sum', 'land', 'lor',
            'lxor', 'band', 'bor', bxor', 'maxloc' and 'minloc'.
            """
            pass

        def allreduce(self, sendbuffer, receivebuffer, operation):
            """Combine data from all processes using |operation|, and
            send the data to all processes in the communicator.

            |operation| is one of the operation objects defined globally
            in the module: 'max', 'min', 'prod', 'sum', 'land', 'lor',
            'lxor', 'band', 'bor', bxor', 'maxloc' and 'minloc'.
            """
            pass

    class MPIRequest:
        """MPI Request

        There is no constructor for MPI Request objects.  They are
        returned by nonblocking send and receives, and are used to
        query the status of the message.
        """

        def wait(self):
            """Waits till the communication has completed.  If the
            operation was a nonblocking send, there is no return value.
            If the operation was a nonblocking receive, the return
            value is a tuple containing four elements: the array
            containing the data, the source process rank (an integer),
            the message tag (an integer), and the number of elements
            that were received (an integer).
            """
            pass

        def test(self):
            """Test if communications have completed.

            If the operation was a nonblocking send, it returns 0 if
            the operation has not completed, and 1 if it has.

            If the operation was a nonblocking receive, 0 is returned
            if the operation was not completed, and a tuple containing
            four elements if it was completed.  The four elements are:
            the array containing the data, the source process rank (an
            integer), the message tag (an integer), and the number of
            elements that were received (an integer).

            Once a test has been successful (i.e. the operation has
            completed), it is no longer possible to call wait() or
            test() on the MPI Request object.
            """
            pass
        
    world = MPICommunicator()
    world.rank = 0
    world.size = 1

    if 0:

        class max:
            """The 'maximum' operation in reduce/allreduce communications."""
            pass

        class min:
            """The 'minimum' operation in reduce/allreduce communications."""
            pass

        class prod:
            """The 'product' operation in reduce/allreduce communications."""
            pass

        class sum:
            """The 'sum' operation in reduce/allreduce communications."""
            pass

        class land:
            """The 'logical and' operation in reduce/allreduce communications."""
            pass

        class lor:
            """The 'logical or' operation in reduce/allreduce communications."""
            pass

        class lxor:
            """The 'logical exclusive-or' operation."""
            pass

        class band:
            """The 'bitwise and' operation in reduce/allreduce communications."""
            pass

        class bor:
            """The 'bitwise or' operation in reduce/allreduce communications."""
            pass

        class bxor:
            """The 'bitwise exclusive-or' operation."""
            pass

        class maxloc:
            """The 'location of the maximum' operation."""
            pass

        class minloc:
            """The 'location of the minimum' operation."""
            pass

        class replace:
            """The 'replace' operation. (MPI 2.0)"""
            pass
        
else:

    try:
        from Scientific_mpi import *
        from Scientific_mpi import _C_API, _registerErrorObject
        _registerErrorObject(MPIError)
        del _registerErrorObject
    except ImportError:

        import Numeric

        _C_API = None

        class DummyCommunicator:

            def __init__(self):
                self.size = 1
                self.rank = 0
                self.messages = []

            def duplicate(self):
                return DummyCommunicator()

            def send(self, data, destination, tag):
                if destination != 0:
                    raise MPIError("invalid MPI destination")
                self.messages.append((tag, Numeric.array(data, copy=1).flat))

            def nonblockingSend(self, data, destination, tag):
                self.send(data, destination, tag)
                return DummyRequest(None)

            def receive(self, array, source=None, tag=None):
                if source != 0 and source != None:
                    raise MPIError("invalid MPI source")
                for i in range(len(self.messages)):
                    data_tag, data = self.messages[i]
                    if tag is None or tag == data_tag:
                        del self.messages[i]
                        return data, 0, data_tag, len(data)
                raise MPIError("no message received")

            def receiveString(self, source=None, tag=None):
                array, source, tag, length = self.receive(source, tag)
                return array.tostring(), source, tag

            def nonblockingReceive(self, array, source=None, tag=None):
                return DummyRequest(self.receive(array, source, tag))

            def nonblockingProbe(self, source=None, tag=None):
                if source != 0 and source != None:
                    raise MPIError, "invalid MPI source"
                for i in range(len(self.messages)):
                    data_tag, data = self.messages[i]
                    if tag is None or tag == data_tag:
                        return 0, data_tag
                return None

            def broadcast(self, array, root):
                if root != 0:
                    raise MPIError("invalid MPI rank")
                return array

            def share(self, send, receive):
                receive[0] = send

            def barrier(self):
                pass

            def abort(self):
                raise MPIError("abort")

        class DummyRequest:

            def __init__(self, arg):
                self.arg = arg

            def wait(self):
                return self.arg

        world = DummyCommunicator()

del sys
