# Coordinated I/O for parallel systems
#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 2000-7-31
#

class LogFile:

    """File for logging events from all processes

    Constructor: LogFile(|filename|, |communicator|=None)

    Arguments:

    |filename| -- the name of the file

    |communicator| -- the communicator in which the file is accesible.
                      The default value of 'None' means to use the
                      global world communicator, i.e. all possible
                      processes.

    The purpose of LogFile objects is to collect short text output from
    all processors into a single file. All processes can write whatever
    they want at any time; the date is simply stored locally.
    After the file has been closed by all processes, the
    data is sent to process 0, which then writes everything to one
    text file, neatly separated by process rank number.

    Note that due to the intermediate storage of the data, LogFile
    objects should not be used for large amounts of data. Also
    note that all data is lost if a process crashes before closing
    the file.
    """

    def __init__(self, filename, communicator = None):
        self.filename = filename
        if communicator is None:
            from Scientific.MPI import world
            self.communicator = world
        else:
            self.communicator = communicator
        self.data = ''
        self.first_chunk = 1

    def write(self, string):
        "Write |string| to the file."
        self.data = self.data + string

    def flush(self):
        "Write buffered data to the text file."
        if self.communicator.rank == 0:
            if self.filename is None:
                import sys
                file = sys.stdout
            else:
                if self.first_chunk:
                    file = open(self.filename, 'w')
                else:
                    file = open(self.filename, 'a')
            if not self.first_chunk:
                file.write(75*'='+'\n')
            file.write("Rank 0:\n\n")
            file.write(self.data)
            file.write("\n\n")
            for i in range(1, self.communicator.size):
                file.write("Rank %d:\n\n" % i)
                data = self.communicator.receiveString(i, 0)[0]
                file.write(data)
                file.write("\n\n")
            if self.filename is not None:
                file.close()
        else:
            self.communicator.send(self.data, 0, 0)
        self.data = ''
        self.first_chunk = 0

    def close(self):
        "Close the file, causing the real text file to be written."
        self.flush()
