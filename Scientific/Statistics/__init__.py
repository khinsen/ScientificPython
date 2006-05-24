# Basic statistics functions.
#
# Written by Konrad Hinsen <khinsen@cea.fr>
# With contributions from Moshe Zadka <mzadka@geocities.com>
# last revision: 2005-9-5
#

from Scientific import N

#
# Univariate statistics functions
#

def moment(data, order, about=None, theoretical=1):
    data = 1.*N.array(data)
    if about is None:
        about = mean(data)
        theoretical = 0
    ln = len(data)-(1-theoretical)
    return 1.*N.add.reduce((data-about)**order)/ln

def mean(data):
    "Returns the mean (average value) of |data| (a sequence of numbers)."
    return moment(data, 1, 0)

average = mean

def weightedMean(data, sigma):
    """Weighted mean of a sequence of numbers with given standard deviations.

    |data| is a list of measurements,
    |sigma| a list with corresponding standard deviations.

    Returns weighted mean and corresponding standard deviation.
    """
    from Numeric import array, Float, sqrt, sum
    if len(data) != len(sigma):
        raise ValueError
    data = 1.*N.array(data)
    sigma = 1.*N.array(sigma)
    nom = sum(data/sigma**2)
    denom = sum(1./sigma**2)
    mean = nom / denom
    sig = sqrt(1./denom)
    return mean, sig

def variance(data):
    "Returns the variance of |data| (a sequence of numbers)."
    return moment(data, 2)

def standardDeviation(data):
    "Returns the standard deviation of |data| (a sequence of numbers)."
    return N.sqrt(variance(data))

def median(data):
    "Returns the median of |data| (a sequence of numbers)."
    data = N.sort(N.array(data))
    l = (len(data)-1)/2.
    return (data[int(N.floor(l))]+data[int(N.ceil(l))])/2.

def mode(data):
    h = {}
    for n in data:
        try: h[n] = h[n]+1
        except KeyError: h[n] = 1
    a = map(lambda x: (x[1], x[0]), h.items())
    return max(a)[1]

def normalizedMoment(data, order):
    mn = mean(data)
    return moment(data, order, mn)/N.sqrt(moment(data, 2, mn)**order)

def skewness(data):
    "Returns the skewness of |data| (a sequence of numbers)."
    return normalizedMoment(data, 3)

def kurtosis(data):
    "Returns the kurtosis of |data| (a sequence of numbers)."
    return normalizedMoment(data, 4)

##  def chiSquare(data):
##      h = {}
##      for n in data:
##         try: h[n] = h[n]+1
##         except KeyError: h[n] = 1
##      h = N.array(h.values())
##      h = h/N.add.reduce(h)
##      return moment(h, 2, 1./len(h))

def correlation(data1, data2):
    """Returns the correlation coefficient between |data1| and |data2|,
    which must have the same length."""
    if len(data1) != len(data2):
        raise ValueError("data series must have equal length")
    data1 = N.array(data1)
    data2 = N.array(data2)
    data1 = data1 - N.add.reduce(data1)/len(data1)
    data2 = data2 - N.add.reduce(data2)/len(data2)
    return N.add.reduce(data1*data2) / \
           N.sqrt(N.add.reduce(data1*data1) \
                        * N.add.reduce(data2*data2))
