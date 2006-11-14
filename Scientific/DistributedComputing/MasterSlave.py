#
# Master/slave process manager for distributed computing
# based on Pyro
#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 2006-11-14
#

from Scientific.DistributedComputing.TaskManager import \
                      TaskManager, TaskManagerTermination, TaskRaisedException
import Pyro.core
import Pyro.naming
import Pyro.errors
import threading
import time
import copy
import sys

class MasterProcess(object):
    
    def __init__(self, label, use_name_server=True):
        self.label = label
        self.task_manager = TaskManager()
        self.process_id = self.task_manager.registerProcess()
        Pyro.core.initServer(banner=False)
        self.pyro_ns = None
        if use_name_server:
            self.pyro_ns=Pyro.naming.NameServerLocator().getNS()
        self.manager_thread = threading.Thread(target = self.taskManagerThread)
        self.manager_thread.start()

    def taskManagerThread(self):
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
        if self.pyro_ns is not None:
            try:
                self.pyro_ns.unregister(":TaskManager.%s" % self.label)
            except Pyro.errors.NamingError:
                pass

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

    def __init__(self, label, master_host=None):
        Pyro.core.initClient(banner=False)
        if master_host is None:
            self.task_manager = \
                Pyro.core.getProxyForURI("PYRONAME://:TaskManager.%s" % label)
        else:
            # URI defaults to "PYROLOC://localhost:7766/"
            uri = "PYROLOC://%s/TaskManager.%s" % (master_host, label)
            self.task_manager = Pyro.core.getProxyForURI(uri)
        # Do a ping every minute - maybe this will become a parameter later on
        self.watchdog_period = 60.
        self.done = False

    def watchdogThread(self):
        task_manager = copy.copy(self.task_manager)
        while True:
            task_manager.ping(self.process_id)
            if self.done:
                break
            time.sleep(self.watchdog_period)

    def start(self):
        self.process_id = \
            self.task_manager.registerProcess(self.watchdog_period)
        self.background_thread = threading.Thread(target=self.watchdogThread)
        self.background_thread.setDaemon(True)
        self.background_thread.start()
        while True:
            try:
                task_id, tag, parameters = \
                       self.task_manager.getAnyTask(self.process_id)
            except TaskManagerTermination:
                break
            try:
                method = getattr(self, "do_%s" % tag)
            except AttributeError:
                self.task_manager.returnTask(task_id)
                continue
            try:
                result = method(*parameters)
            except KeyboardInterrupt:
                self.task_manager.returnTask(task_id)
                self.task_manager.unregisterProcess(self.process_id)
                raise
            except Exception, e:
                import traceback, StringIO
                tb_text = StringIO.StringIO()
                traceback.print_exc(None, tb_text)
                tb_text = tb_text.getvalue()
                self.task_manager.storeException(task_id, e, tb_text)
            else:
                self.task_manager.storeResult(task_id, result)
        self.task_manager.unregisterProcess(self.process_id)
        self.done = True
