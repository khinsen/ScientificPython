#
# Task manager for distributed computing based on Pyro
#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 2006-11-9
#

import Pyro.core
import threading
import time

debug = False

class TaskManagerTermination(Exception):
    pass

class Task(object):
    
    def __init__(self, tag, parameters, task_id):
        self.tag = tag
        self.parameters = parameters
        self.id = task_id
        self.requesting_processor = None
        self.handling_processor = None
        self.request_time = None
        self.start_time = None
        self.end_time = None

class TaskList(object):

    def __init__(self):
        self.tasks = []
        self.tasks_by_tag = {}
        self.tasks_by_id = {}
        self.task_available = threading.Condition()
        self.terminate = False

    def __len__(self):
        return len(self.tasks)

    def terminateWaitingThreads(self):
        self.task_available.acquire()
        self.terminate = True
        self.task_available.notifyAll()
        self.task_available.release()

    def _checkForTermination(self):
        if self.terminate:
            self.task_available.release()
            raise TaskManagerTermination()

    def addTask(self, task):
        self.task_available.acquire()
        self.tasks.append(task)
        tasks = self.tasks_by_tag.setdefault(task.tag, [])
        tasks.append(task)
        self.tasks_by_id[task.id] = task
        self.task_available.notifyAll()
        self.task_available.release()

    def firstTask(self):
        self.task_available.acquire()
        while not self.tasks:
            self._checkForTermination()
            self.task_available.wait()
        task = self.tasks[0]
        self._removeTask(task)
        self.task_available.release()
        return task

    def firstTaskWithTag(self, tag):
        self.task_available.acquire()
        while not self.tasks_by_tag.get(tag, None):
            self._checkForTermination()
            self.task_available.wait()
        task = self.tasks_by_tag[tag][0]
        self._removeTask(task)
        self.task_available.release()
        return task

    def taskWithId(self, task_id):
        self.task_available.acquire()
        while True:
            task = self.tasks_by_id.get(task_id, None)
            if task is not None:
                break
            self._checkForTermination()
            self.task_available.wait()
        self._removeTask(task)
        self.task_available.release()
        return task

    def _removeTask(self, task):
        self.tasks.remove(task)
        self.tasks_by_tag[task.tag].remove(task)
        del self.tasks_by_id[task.id]


class TaskManager(Pyro.core.ObjBase):

    def __init__(self):
        Pyro.core.ObjBase.__init__(self)
        self.id_counter = 0
        self.waiting_tasks = TaskList()
        self.running_tasks = TaskList()
        self.finished_tasks = TaskList()
        self.results = {}
        self.process_counter = 0
        self.active_processes = []
        self.lock = threading.Lock()

    def registerProcess(self):
        self.lock.acquire()
        process_id = self.process_counter
        self.process_counter += 1
        self.active_processes.append(process_id)
        self.lock.release()
        return process_id

    def unregisterProcess(self, process_id):
        self.lock.acquire()
        self.active_processes.remove(process_id)
        self.lock.release()

    def numberOfActiveProcesses(self):
        return len(self.active_processes)

    def addTaskRequest(self, tag, parameters, process_id=None):
        self.lock.acquire()
        task_id = tag + '_' + str(self.id_counter)
        self.id_counter += 1
        self.lock.release()
        new_task = Task(tag, parameters, task_id)
        if process_id:
            new_task.requesting_processor = process_id
        new_task.request_time = time.time()
        self.waiting_tasks.addTask(new_task)
        if debug:
            print "Task request %s: %s(%s)" % (task_id, tag, str(parameters))
        return task_id

    def getTaskWithTag(self, tag, process_id=None):
        task = self.waiting_tasks.firstTaskWithTag(tag)
        self._checkoutTask(task, process_id)
        return task.id, task.parameters

    def getAnyTask(self, process_id=None):
        task = self.waiting_tasks.firstTask()
        self._checkoutTask(task, process_id)
        return task.id, task.tag, task.parameters

    def _checkoutTask(self, task, process_id):
        task.handling_processor = process_id
        task.start_time = time.time()
        self.running_tasks.addTask(task)
        if debug:
            print "Handing out task %s to process %d" % (task.id, process_id)

    def storeResult(self, task_id, result):
        if debug:
            print "Task %s yielded result %s" % (task_id, result)
        self.lock.acquire()
        self.results[task_id] = result
        self.lock.release()
        task = self.running_tasks.taskWithId(task_id)
        task.end_time = time.time()
        self.finished_tasks.addTask(task)

    def storeException(self, task_id, exception):
        if debug:
            print "Task %s raised exception %s" % (task_id, exception)
        self.lock.acquire()
        self.results[task_id] = exception
        self.lock.release()
        task = self.running_tasks.taskWithId(task_id)
        task.end_time = time.time()
        self.finished_tasks.addTask(task)

    def returnTask(self, task_id):
        if debug:
            print "Task %s returned" % task_id
        task = self.running_tasks.taskWithId(task_id)
        task.start_time = None
        task.handling_processor = None
        self.waiting_tasks.addTask(task)
        
    def getAnyResult(self):
        task = self.finished_tasks.firstTask()
        result = self.results[task.id]
        del self.results[task.id]
        return task.id, task.tag, result

    def getResultWithTag(self, tag):
        task = self.finished_tasks.firstTaskWithTag(tag)
        result = self.results[task.id]
        del self.results[task.id]
        if debug:
            print "Handed out result of %s" % task.id
        return task.id, result

    def terminate(self):
        if debug:
            print "Terminating"
        self.waiting_tasks.terminateWaitingThreads()
        self.running_tasks.terminateWaitingThreads()
        self.finished_tasks.terminateWaitingThreads()
