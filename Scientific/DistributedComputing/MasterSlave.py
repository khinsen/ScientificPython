#
# Master/slave process manager for distributed computing
# based on Pyro
#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 2006-11-6
#

# Ideas:
# - Give each slave an id
# - When a slave accepts a task, store its id
# - Add a thread to slaves that makes them ping the manager regularly.
# - When no ping arrives, the manager removes the slave and puts its
#   tasks back on the waiting list.

from Scientific.DistributedComputing.TaskManager import TaskManager
import Pyro.core
import Pyro.naming
import threading

class MasterProcess(object):
    
    def __init__(self, label):
        self.task_manager = TaskManager()
        self.label = label
        self.manager_thread = threading.Thread(target = self.taskManagerThread)
        self.manager_thread.start()

    def taskManagerThread(self):
        Pyro.core.initServer()
        self.pyro_daemon=Pyro.core.Daemon()
        uri = self.pyro_daemon.connect(self.task_manager,
                                       "TaskManager.%s" % self.label)
        print "The TaskManager's uri is:", uri
        self.pyro_daemon.requestLoop()

    def requestTask(self, tag, *parameters):
        self.task_manager.addTaskRequest(tag, parameters)

    def retrieveResult(self, tag):
        while True:
            task_id, result = self.task_manager.getResultWithTag(tag)
            if task_id is not None:
                return task_id, result

    def run(self):
        self.mainloop()
        self.task_manager.signalTermination()
        # For now, just wait a bit...
        import time
        time.sleep(5)
        self.pyro_daemon.shutdown()
        self.manager_thread.join()

    def mainloop(self):
        raise NotImplementedError


class SlaveProcess(object):
    
    def __init__(self, label):
        self.task_manager = \
            Pyro.core.getProxyForURI("PYROLOC://localhost:7766/TaskManager.%s"
                                     % label)

    def run(self):
        self._mainloop()

    def _mainloop(self):
        while not self.task_manager.allDone():
            task_id, tag, parameters = self.task_manager.getAnyTask()
            method = getattr(self, "run_%s" % tag)
            result = method(*parameters)
            self.task_manager.storeResult(task_id, result)
