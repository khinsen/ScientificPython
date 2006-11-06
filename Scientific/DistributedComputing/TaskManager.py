#
# Task manager for distributed computing based on Pyro
#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 2006-11-6
#

import Pyro.core
import threading

debug = False

class Task(object):
    
    def __init__(self, tag, parameters, task_id):
        self.tag = tag
        self.parameters = parameters
        self.id = task_id
        self.processor_id = None
        self.started = None
        self.ended = None

class TaskList(object):

    def __init__(self):
        self.tasks = []
        self.tasks_by_tag = {}
        self.tasks_by_id = {}
        self.lock = threading.Lock()

    def __len__(self):
        return len(self.tasks)

    def addTask(self, task):
        self.lock.acquire()
        self.tasks.append(task)
        tasks = self.tasks_by_tag.setdefault(task.tag, [])
        tasks.append(task)
        self.tasks_by_id[task.id] = task
        self.lock.release()

    def firstTask(self):
        self.lock.acquire()
        task = None
        if self.tasks:
            task = self.tasks[0]
            self._removeTask(task)
        self.lock.release()
        return task

    def firstTaskWithTag(self, tag):
        self.lock.acquire()
        task = None
        if self.tasks_by_tag.has_key(tag):
            tasks = self.tasks_by_tag[tag]
            if tasks:
                task = tasks[0]
                self._removeTask(task)
        self.lock.release()
        return task

    def taskWithId(self, task_id):
        self.lock.acquire()
        task = self.tasks_by_id.get(task_id, None)
        self._removeTask(task)
        self.lock.release()
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
        self.all_done = False
        self.lock = threading.Lock()

    def addTaskRequest(self, tag, parameters):
        self.lock.acquire()
        task_id = tag + '_' + str(self.id_counter)
        self.id_counter += 1
        self.lock.release()
        new_task = Task(tag, parameters, task_id)
        self.waiting_tasks.addTask(new_task)
        if debug:
            print "Task request %s: %s(%s)" % (task_id, tag, str(parameters))
        return task_id

    def getTaskWithTag(self, tag):
        task = self.waiting_tasks.firstTaskWithTag(tag)
        if task is None:
            return None, None
        else:
            self.running_tasks.addTask(task)
            if debug:
                print "Handing out task %s" % task.id
            return task.id, task.parameters

    def getAnyTask(self):
        task = self.waiting_tasks.firstTask()
        if task is None:
            return None, None, None
        else:
            self.running_tasks.addTask(task)
            if debug:
                print "Handing out task %s" % task.id
            return task.id, task.tag, task.parameters

    def storeResult(self, task_id, result):
        if debug:
            print "Task %s yielded result %s" % (task_id, result)
        self.lock.acquire()
        self.results[task_id] = result
        self.lock.release()
        task = self.running_tasks.taskWithId(task_id)
        self.finished_tasks.addTask(task)

    def getAnyResult(self):
        task = self.finished_tasks.firstTask()
        if task is None:
            return None, None, None
        else:
            result = self.results[task.id]
            del self.results[task.id]
            return task.id, task.tag, result

    def getResultWithTag(self, tag):
        task = self.finished_tasks.firstTaskWithTag(tag)
        if task is None:
            return None, None
        else:
            result = self.results[task.id]
            del self.results[task.id]
            if debug:
                print "Handed out result of %s" % task.id
            return task.id, result

    def signalTermination(self):
        if debug:
            print "All done!"
        self.all_done = True

    def allDone(self):
        return self.all_done
