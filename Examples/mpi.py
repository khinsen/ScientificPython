from Scientific import MPI
import Numeric, sys

communicator = MPI.world.duplicate()

# Send and receive

if communicator.rank == 0:

    data = 1.*Numeric.arange(10)
    communicator.send(data, 1, 0)
    print "%d sent:\n%s" % (communicator.rank, str(data))

    data, source, tag = communicator.receiveString(1, None)
    print "%d received string from %d: %s" % (communicator.rank, source, data)

elif communicator.rank == 1:

    data, source, tag, count = \
          communicator.receive(Numeric.Float, None, None)
    print "%d received from %d:\n%s" \
          % (communicator.rank, source, str(data))

    communicator.send("Hello world", 0, 42)

else:

    print "%d idle" % communicator.rank

# Barrier

print "%d waiting at barrier" % communicator.rank
sys.stdout.flush()
communicator.barrier()
print "%d passed barrier" % communicator.rank
sys.stdout.flush()

# Broadcast

data = Numeric.zeros((5,), Numeric.Float)
if communicator.rank == 0:
    data[:] = 42.
communicator.broadcast(data, 0)
print "%d has:\n   %s" % (communicator.rank, str(data))

sys.stdout.flush()
communicator.barrier()

# Reduce
data_send = (communicator.rank+1) * Numeric.arange(3)
data_recv = Numeric.zeros(3)
communicator.reduce(data_send, data_recv, MPI.sum, 0)
print "%d has:\n   %s" % (communicator.rank, str(data_recv))

# Share

to_share = (communicator.rank+1)*Numeric.arange(5)
all = Numeric.zeros((communicator.size,)+to_share.shape, to_share.typecode())
communicator.share(to_share, all)
print "%d has:\n%s" % (communicator.rank, str(all))
