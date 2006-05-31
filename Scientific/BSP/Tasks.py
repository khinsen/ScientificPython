# Task lists with automatic load balancing
#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 2004-12-13
#

from Scientific.BSP.core import ParBase, ParClass, ParInvalid
import operator
from time import clock

class ParTaskBase:

    def __init__(self):
        pass

    def step(self, messages):
        raise NotImplementedError

    def setIndex(self, index, total):
        pass


class _ParTaskList(ParBase):

    def __parinit__(self, pid, nprocs):
        self.tasks = []
        self.new_tasks = []
        self.pid = pid
        self.nprocs = nprocs
        self.index_map = {}
        self.pid_from_index = []

    def addTask(self, task):
        if task is not ParInvalid:
            self.new_tasks.append(task)

    def step(self, *args, **kwargs):
        # Insert any new tasks into task list
        if self.new_tasks:
            # Send number of tasks and number of new tasks to root
            counts = self.put((self.pid, len(self.tasks), len(self.new_tasks)),
                              [0])
            # Root determines the first new task index for each processor
            ntot = 0
            for pid, nt, nnt in counts:
                ntot += nt
            messages = []
            for pid, nt, nnt in counts:
                messages.append((pid, ntot))
                ntot += nnt
            index = self.exchangeMessages(messages)[0]
            # Add new task to task list and set index
            for task in self.new_tasks:
                task._index = index
                task._messages = []
                task.setIndex(index, ntot)
                index += 1
                self.tasks.append(task)
            self.new_tasks = []
            # Update index map
            self.index_map = {}
            for i in range(len(self.tasks)):
                self.index_map[self.tasks[i]._index] = i
            # Update pid map
            indices = map(lambda t: t._index, self.tasks)
            all = self.put((pid, indices), [0])
            all = self.broadcast(all)
            self.pid_from_index = ntot*[None]
            for pid, indices in all:
                for index in indices:
                    self.pid_from_index[index] = pid
        # Run all tasks and record the time used by each
        start = clock()
        total = 0
        messages = []
        for task in self.tasks:
            messages += task.step(task._messages)
            end = clock()
            task._time = end-start
            total += end-start
            start = end
        # Distribute messages
        to_send = []
        for i in range(self.nprocs):
            to_send.append([])
        for index, data in messages:
            pid = self.pid_from_index[index]
            to_send[pid].append((index, data))
        my_messages = to_send[self.pid]
        messages = []
        for pid in range(self.nprocs):
            if pid != self.pid:
                messages.append((pid, to_send[pid]))
        my_messages += reduce(operator.add, self.exchangeMessages(messages),
                              [])
        for task in self.tasks:
            task._messages = []
        for index, data in my_messages:
            self.tasks[self.index_map[index]]._messages.append(data)
        # Root calculates the runtime discrepancy
        messages = self.put((pid, total), [0])
        times = map(lambda x: x[1], messages)
        if self.pid == 0:
            average = N.sum(times)/len(times)
            discrepancy = N.maximum.reduce(times)-N.minimum.reduce(times)
            #print discrepancy, average

ParTaskList = ParClass(_ParTaskList)


if __name__ == '__main__':

    from Scientific.BSP.core import ParValue, ParSequence, ParIterator

    class _SimpleTask(ParTaskBase):

        def __init__(self, value):
            self.value = [value]

        def __repr__(self):
            return "SimpleTask(%s)" % repr(self.value)

        def setIndex(self, index, total):
            self.neighbour = (index+1)%total

        def step(self, messages):
            try:
                self.value.append(messages[0])
            except IndexError:
                pass
            return [(self.neighbour, self.value[-1])]

    SimpleTask = ParValue(_SimpleTask)
    tasks = ParTaskList()
    for i in ParIterator(ParSequence(range(10))):
        tasks.addTask(SimpleTask(i))
    for i in range(5):
        tasks.step()
        print tasks.tasks
