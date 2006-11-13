#
# Master/slave process manager for distributed computing
# based on Pyro
#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 2006-11-13
#

# Ideas:
# - Give each slave an id
# - When a slave accepts a task, store its id
# - Add a thread to slaves that makes them ping the manager regularly.
# - When no ping arrives, the manager removes the slave and puts its
#   tasks back on the waiting list.

from Scientific.DistributedComputing.TaskManager import \
                                     TaskManager, TaskManagerTermination
import Pyro.core
import Pyro.naming
import Pyro.errors
import threading
import time

class MasterProcess(object):
    
    def __init__(self, label, use_name_server=True):
        self.label = label
        self.task_manager = TaskManager()
        self.process_id = self.task_manager.registerProcess()
        self.pyro_ns = None
        if use_name_server:
            self.pyro_ns=Pyro.naming.NameServerLocator().getNS()
        self.manager_thread = threading.Thread(target = self.taskManagerThread)
        self.manager_thread.start()

    def taskManagerThread(self):
        Pyro.core.initServer(banner=False)
        self.pyro_daemon=Pyro.core.Daemon()
        if self.pyro_ns is not None:
            self.pyro_daemon.useNameServer(self.pyro_ns)
            try:
                self.pyro_ns.createGroup(":TaskManager")
            except Pyro.errors.NamingError:
                pass
            uri = self.pyro_daemon.connect(self.task_manager,
                                           ":TaskManager.%s" % self.label)
        else:
            uri = self.pyro_daemon.connect(self.task_manager,
                                           "TaskManager.%s" % self.label)
        try:
            self.pyro_daemon.requestLoop()
        finally:
            self.pyro_daemon.shutdown(True)

    def requestTask(self, tag, *parameters):
        self.task_manager.addTaskRequest(tag, parameters)

    def retrieveResult(self, tag=None):
        try:
            if tag is None:
                return self.task_manager.getAnyResult()
            else:
                task_id, result = self.task_manager.getResultWithTag(tag)
                return task_id, tag, result
        except TaskManagerTermination:
            return None, None, None

    def start(self):
        try:
            self.run()
        finally:
            self.task_manager.terminate()
            while self.task_manager.numberOfActiveProcesses() > 1:
                time.sleep(0.1)
            self.pyro_daemon.shutdown()
            self.manager_thread.join()

    def run(self):
        raise NotImplementedError


class SlaveProcess(object):

    def __init__(self, label, master_uri=None):
        Pyro.core.initClient(banner=False)
        if master_uri is None:
            self.task_manager = \
                Pyro.core.getProxyForURI("PYRONAME://:TaskManager.%s" % label)
        else:
            # URI defaults to "PYROLOC://localhost:7766/"
            uri = master_uri + "TaskManager.%s" % label
            self.task_manager = Pyro.core.getProxyForURI(uri)
        self.process_id = self.task_manager.registerProcess()

    def start(self):
        while True:
            try:
                task_id, tag, parameters = self.task_manager.getAnyTask()
            except TaskManagerTermination:
                break
            try:
                method = getattr(self, "do_%s" % tag)
            except AttributeError:
                self.task_manager.returnTask(task_id)
                continue
            try:
                result = method(*parameters)
            except Exception, e:
                self.task_manager.storeException(task_id, e)
            else:
                self.task_manager.storeResult(task_id, result)
        self.task_manager.unregisterProcess(self.process_id)
