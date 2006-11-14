#
# Task manager for distributed computing based on Pyro
#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 2006-11-14
#

import Pyro.core
import threading
import time

debug = False

class TaskManagerTermination(Exception):
    pass

class TaskRaisedException(Exception):
    
    def __init__(self, task_id, tag, exception, traceback):
        self.task_id = task_id
        self.tag = tag
        self.exception = exception
        self.traceback = traceback

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

class TaskQueue(object):

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

    def addTask(self, task, in_front=False):
        self.task_available.acquire()
        self.tasks.append(task)
        tasks = self.tasks_by_tag.setdefault(task.tag, [])
        if in_front:
            tasks.insert(0, task)
        else:
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
        self.waiting_tasks = TaskQueue()
        self.running_tasks = TaskQueue()
        self.finished_tasks = TaskQueue()
        self.results = {}
        self.process_counter = 0
        self.active_processes = []
        self.tasks_by_process = []
        self.lock = threading.Lock()
        self.watchdog = None

    def registerProcess(self, watchdog_period=None):
        self.lock.acquire()
        process_id = self.process_counter
        self.process_counter += 1
        self.active_processes.append(process_id)
        self.tasks_by_process.append([])
        self.lock.release()
        if watchdog_period is not None:
            if self.watchdog is None:
                self.watchdog = Watchdog(self)
            self.watchdog.registerProcess(process_id, watchdog_period)
        return process_id

    def unregisterProcess(self, process_id):
        if debug:
            print "Unregistering process", process_id
        self.lock.acquire()
        self.active_processes.remove(process_id)
        tasks = self.tasks_by_process[process_id]
        self.tasks_by_process[process_id] = []
        self.lock.release()
        for t in tasks:
            self.returnTask(t.id)
        if self.watchdog is not None:
            self.watchdog.unregisterProcess(process_id)

    def ping(self, process_id):
        if self.watchdog is not None:
            self.watchdog.ping(process_id)

    def numberOfActiveProcesses(self):
        return len(self.active_processes)

    def numberOfTasks(self):
        self.lock.acquire()
        nwaiting = len(self.waiting_tasks)
        nrunning = len(self.running_tasks)
        nfinished = len(self.finished_tasks)
        self.lock.release()
        return nwaiting, nrunning, nfinished

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
        if process_id is not None:
            self.lock.acquire()
            self.tasks_by_process[process_id].append(task)
            self.lock.release()
        if debug:
            print "Handing out task %s to process %s" \
                  % (task.id, str(process_id))

    def storeResult(self, task_id, result):
        if debug:
            print "Task %s yielded result %s" % (task_id, result)
        self.lock.acquire()
        self.results[task_id] = result
        self.lock.release()
        task = self.running_tasks.taskWithId(task_id)
        task.end_time = time.time()
        task.completed = True
        self.finished_tasks.addTask(task)
        self._removeTask(task)

    def storeException(self, task_id, exception, traceback):
        if debug:
            print "Task %s raised exception %s" % (task_id, exception)
        self.lock.acquire()
        self.results[task_id] = (exception, traceback)
        self.lock.release()
        task = self.running_tasks.taskWithId(task_id)
        task.end_time = time.time()
        task.completed = False
        self.finished_tasks.addTask(task)
        self._removeTask(task)

    def returnTask(self, task_id):
        if debug:
            print "Task %s returned" % task_id
        task = self.running_tasks.taskWithId(task_id)
        self._removeTask(task)
        task.start_time = None
        task.handling_processor = None
        self.waiting_tasks.addTask(task, in_front=True)
        
    def _removeTask(self, task):
        if task.handling_processor is not None:
            self.lock.acquire()
            try:
                self.tasks_by_process[task.handling_processor].remove(task)
            except ValueError:
                pass
            self.lock.release()

    def getAnyResult(self):
        task = self.finished_tasks.firstTask()
        result = self.results[task.id]
        del self.results[task.id]
        if task.completed:
            return task.id, task.tag, result
        else:
            raise TaskRaisedException(task.id, task.tag, result[0], result[1])

    def getResultWithTag(self, tag):
        task = self.finished_tasks.firstTaskWithTag(tag)
        result = self.results[task.id]
        del self.results[task.id]
        if debug:
            print "Handed out result of %s" % task.id
        if task.completed:
            return task.id, result
        else:
            raise TaskRaisedException(task.id, task.tag, result[0], result[1])

    def terminate(self):
        if debug:
            print "Terminating"
        self.waiting_tasks.terminateWaitingThreads()
        self.running_tasks.terminateWaitingThreads()
        self.finished_tasks.terminateWaitingThreads()


class Watchdog(object):

    def __init__(self, task_manager):
        self.task_manager = task_manager
        self.ping_period = {}
        self.last_ping = {}
        self.done = False
        self.lock = threading.Lock()
        self.background_thread = threading.Thread(target = self.watchdogThread)
        self.background_thread.setDaemon(True)
        self.thread_started = False

    def registerProcess(self, process_id, ping_period):
        self.lock.acquire()
        self.ping_period[process_id] = ping_period
        self.last_ping[process_id] = time.time()
        self.lock.release()
        if not self.thread_started:
            self.background_thread.start()
            self.thread_started = True

    def unregisterProcess(self, process_id):
        self.lock.acquire()
        try:
            del self.ping_period[process_id]
            del self.last_ping[process_id]
        except KeyError:
            # KeyError happens when processes without watchdog are unregistered
            pass
        self.lock.release()

    def ping(self, process_id):
        self.lock.acquire()
        self.last_ping[process_id] = time.time()
        self.lock.release()

    def terminate(self, blocking=False):
        self.done = True
        if blocking:
            self.background_thread.join()

    def watchdogThread(self):
        while True:
            now = time.time()
            dead_processes = []
            min_delay = min(self.ping_period.values() + [60.])
            self.lock.acquire()
            for process_id in self.ping_period.keys():
                delay = now-self.last_ping[process_id]
                if delay > 2*self.ping_period[process_id]:
                    dead_processes.append(process_id)
            self.lock.release()
            for process_id in dead_processes:
                if debug:
                    print "Process %d died" % process_id
                self.task_manager.unregisterProcess(process_id)
            if self.done:
                break
            time.sleep(min_delay)

