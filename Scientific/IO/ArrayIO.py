# Array I/O to text files
#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 2004-12-13
#

"""This module contains elementary support for I/O of one- and
two-dimensional numerical arrays to and from plain text files. The
text file format is very simple and used by many other programs as
well:

- each line corresponds to one row of the array

- the numbers within a line are separated by white space

- lines starting with # are ignored (comment lines)

An array containing only one line or one column is returned as a
one-dimensional array on reading. One-dimensional arrays are written
as one item per line.

Numbers in files to be read must conform to Python/C syntax.  For
reading files containing Fortran-style double-precision numbers
(exponent prefixed by D), use the module Scientific.IO.FortranFormat.
"""

from Scientific.IO.TextFile import TextFile
from Scientific import N; Numeric = N
import string

def readArray(filename):
    """Return an array containing the data from file |filename|. This
    function works for arbitrary data types (every array element can be
    given by an arbitrary Python expression), but at the price of being
    slow. For large arrays, use readFloatArray or readIntegerArray
    if possible."""
    data = []
    for line in TextFile(filename):
        if len(line) == 0 and len(data) > 0:
            break
        if line[0] != '#':
            data.append(map(eval, string.split(line)))
    a = Numeric.array(data)
    if a.shape[0] == 1 or a.shape[1] == 1:
        a = Numeric.ravel(a)
    return a

def readFloatArray(filename):
    "Return a floating-point array containing the data from file |filename|."
    data = []
    for line in TextFile(filename):
        if line[0] != '#':
            data.append(map(string.atof, string.split(line)))
    a = Numeric.array(data)
    if a.shape[0] == 1 or a.shape[1] == 1:
        a = Numeric.ravel(a)
    return a

def readIntegerArray(filename):
    "Return an integer array containing the data from file |filename|."
    data = []
    for line in TextFile(filename):
        if line[0] != '#':
            data.append(map(string.atoi, string.split(line)))
    a = Numeric.array(data)
    if a.shape[0] == 1 or a.shape[1] == 1:
        a = Numeric.ravel(a)
    return a

def writeArray(array, filename, mode='w'):
    """Write array |a| to file |filename|. |mode| can be 'w' (new file)
       or 'a' (append)."""
    file = TextFile(filename, mode)
    if len(array.shape) == 1:
        array = array[:, Numeric.NewAxis]
    for line in array:
        for element in line:
            file.write(`element` + ' ')
        file.write('\n')
    file.close()

#
# Write several data sets (one point per line) to a text file,
# with a separator line between data sets. This is sufficient
# to make input files for most plotting programs.
#
def writeDataSets(datasets, filename, separator = ''):
    """Write each of the items in the sequence |datasets|
    to the file |filename|, separating the datasets by a line
    containing |separator|. The items in the data sets can be
    one- or two-dimensional arrays or equivalent nested sequences.
    The output file format is understood by many plot programs.
    """
    file = TextFile(filename, 'w')
    nsets = len(datasets)
    for i in range(nsets):
        d = Numeric.array(datasets[i])
        if len(d.shape) == 1:
            d = d[:, Numeric.NewAxis]
        for point in d:
            for number in point:
                file.write(`number` + ' ')
            file.write('\n')
        if (i < nsets-1):
            file.write(separator + '\n')
    file.close()
