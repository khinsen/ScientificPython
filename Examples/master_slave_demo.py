from Scientific.DistributedComputing.MasterSlave import MasterProcess, SlaveProcess
from Scientific import N
import sys

class Master(MasterProcess):
    
    def __init__(self):
        MasterProcess.__init__(self, "test")

    def run(self):
        for i in range(5):
            task_id = self.requestTask("sqrt", float(i))
        for i in range(5):
            task_id, tag, result = self.retrieveResult("sqrt")
            print result

class SquareRoot(SlaveProcess):
    
    def __init__(self):
        SlaveProcess.__init__(self, "test")

    def do_sqrt(self, x):
        return (x, N.sqrt(x))


if len(sys.argv) == 2 and sys.argv[1] == "master":
    master = True
elif len(sys.argv) == 2 and sys.argv[1] == "slave":
    master = False
else:
    print "Argument must be 'master' or 'slave'"
    raise SystemExit

if master:
    process = Master()
else:
    process = SquareRoot()
process.start()
