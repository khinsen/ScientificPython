from Scientific.DistributedComputing.MasterSlave import MasterProcess, SlaveProcess
from Scientific import N
import sys

class Master(MasterProcess):

    def run(self):
        for i in range(5):
            task_id = self.requestTask("sqrt", float(i))
        for i in range(5):
            task_id, tag, result = self.retrieveResult("sqrt")
            print result

class SquareRoot(SlaveProcess):
    
    def do_sqrt(self, x):
        return (x, N.sqrt(x))


if len(sys.argv) == 2 and sys.argv[1] == "master":
    master = True
elif len(sys.argv) == 2 and sys.argv[1] == "slave":
    master = False
else:
    print "Argument must be 'master' or 'slave'"
    raise SystemExit

# By default, the Pyro name server is used. Don't forget to start it!
if True:
    if master:
        process = Master("demo")
    else:
        process = SquareRoot("demo")

# If you do not want to use the name server, the slaves must know
# where the master runs:
if False:
    if master:
        process = Master("demo", use_name_server=False)
    else:
        process = SquareRoot("demo", master_uri="PYROLOC://localhost:7766/")
process.start()
