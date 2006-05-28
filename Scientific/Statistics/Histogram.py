# Histograms.
#
# Written by Konrad Hinsen <khinsen@cea.fr>
# last revision: 2006-5-28
#

"""
Standard and weighted histograms
"""

from Scientific import N

class Histogram:

    """
    Histogram in one variable

    The bin index and the number of points in a bin can be obtained by
    indexing the histogram with the bin number. Application of len()
    yields the number of bins. A histogram thus behaves like a
    sequence of bin index - bin count pairs.
    """

    def __init__(self, data, nbins, range=None):
        """
        @param data: a sequence of data points
        @type data: C{Numeric.array} of C{float} or C{int}
        @param bins: the number of bins into which the data is to be sorted
        @type bins: C{int}
        @param range: a tuple of two values, specifying the lower and
                      the upper end of the interval spanned by the bins.
                      Any data point outside this interval will be ignored.
                      If no range is given, the smallest and largest
                      data values are used to define the interval.
        @type range: C{tuple} or C{NoneType}
        """
        self._setup(data, nbins, range)
        self.addData(data)

    def _setup(self, data, nbins, range):
        if range is None:
            self.min = N.minimum.reduce(data)
            self.max = N.maximum.reduce(data)
        else:
            self.min, self.max = range
        self.min = self.min+0.
        self.max = self.max+0.
        self.bin_width = (self.max-self.min)/nbins
        self.array = N.zeros((nbins, 2), N.Float)
        self.array[:, 0] = self.min + self.bin_width*(N.arange(nbins)+0.5)

    def __len__(self):
        """
        @returns: the number of bins
        @rtype: C{int}
        """
        return self.array.shape[0]

    def __getitem__(self, index):
        """
        @param index: a bin index
        @type index: C{int}
        @returns: an array of shape (2,) containing the bin value and the
                  bin count
        """
        return self.array[index]

    def __getslice__(self, first, last):
        return self.array[first:last]

    def addData(self, data):
        """
        Add values to the originally supplied data sequence. Use this
        method to feed long data sequences in multiple parts to avoid
        memory shortages.

        @param data: a sequence of data points
        @type data: C{Numeric.array}
        @Note: this does not affect the default range of the histogram,
               which is fixed when the histogram is created.
        """
        n = (len(data)+999)/1000
        for i in range(n):
            self._addData(data[1000*i:1000*(i+1)])

    def _addData(self, data):
        data = N.array(data, N.Float)
        data = N.repeat(data, N.logical_and(N.less_equal(data, self.max),
                                            N.greater_equal(data, self.min)))
        data = N.floor((data - self.min)/self.bin_width).astype(N.Int)
        nbins = self.array.shape[0]
        histo = N.int_sum(N.equal(N.arange(nbins)[:,N.NewAxis], data), -1)
        histo[-1] = histo[-1] + N.int_sum(N.equal(nbins, data))
        self.array[:, 1] =  self.array[:, 1] + histo

    def normalize(self, norm=1.):
        """
        Scale all bin counts by the same factor

        @param norm: the sum of all bin counts after the rescaling
        @type norm: C{float} or C{int}
        """
        self.array[:, 1] = norm*self.array[:, 1]/N.add.reduce(self.array[:, 1])

    def normalizeArea(self, norm=1.):
        """
        Scale all bin counts by the same factor

        @param norm: the area under the histogram after the rescaling
        @type norm: C{float} or C{int}
        """
        self.normalize(norm/self.bin_width)


class WeightedHistogram(Histogram):

    """
    Weighted histogram in one variable

    Constructor: WeightedHistogram(|data|, |weights|, |bins|, |range|=None)

    Arguments:

    In a weighted histogram, each point has a specific weight. If all
    weights are one, the result is equivalent to a standard histogram.
    The bin index and the number of points in a bin can be obtained by
    indexing the histogram with the bin number. Application of len()
    yields the number of bins. A histogram thus behaves like a
    sequence of bin index - bin count pairs.
    """

    def __init__(self, data, weights, nbins, range=None):
        """
        @param data: a sequence of data points
        @type data: C{Numeric.array}
        @param weights: a sequence of weights, same length as data
        @type weights: C{Numeric.array}
        @param bins: the number of bins into which the data is to be sorted
        @type bins: C{int}
        @param range: a tuple of two values, specifying the lower and
                      the upper end of the interval spanned by the bins.
                      Any data point outside this interval will be ignored.
                      If no range is given, the smallest and largest
                      data values are used to define the interval.
        @type range: C{tuple} or C{NoneType}
        """
        if len(data) != len(weights):
            raise ValueError("wrong number of weights")
        self._setup(data, nbins, range)
        self.addData(data, weights)

    def addData(self, data, weights):
        """
        Add values to the originally supplied data sequence. Use this
        method to feed long data sequences in multiple parts to avoid
        memory shortages.

        @param data: a sequence of data points
        @type data: C{Numeric.array}
        @Note: this does not affect the default range of the histogram,
               which is fixed when the histogram is created.
        """
        if len(data) != len(weights):
            raise ValueError("wrong number of weights")
        n = (len(data)+999)/1000
        for i in range(n):
            self._addData(data[1000*i:1000*(i+1)], weights[1000*i:1000*(i+1)])

    def _addData(self, data, weights):
        data = N.array(data, N.Float)
        weights = N.array(weights, N.Float)
        mask = N.logical_and(N.less_equal(data, self.max),
                             N.greater_equal(data, self.min))
        data = N.repeat(data, mask)
        weights = N.repeat(weights, mask)
        data = N.floor((data - self.min)/self.bin_width).astype(N.Int)
        nbins = self.array.shape[0]
        histo = N.add.reduce(weights*N.equal(N.arange(nbins)[:,N.NewAxis],
                                             data), -1)
        histo[-1] = histo[-1] + N.add.reduce(N.repeat(weights,
                                                      N.equal(nbins, data)))
        self.array[:, 1] =  self.array[:, 1] + histo


if __name__ == '__main__':

    from Gnuplot import plot

    data = N.arange(50000.)**2
    h = Histogram(data, 10)
