# This module provides interpolation for functions defined on a grid.
#
# Written by Konrad Hinsen <khinsen@cea.fr>
# last revision: 2005-9-5
#

from Scientific import N; Numeric = N
import Polynomial
from Scientific.indexing import index_expression
import operator

#
# General interpolating functions.
#
class InterpolatingFunction:

    """Function defined by values on a grid using interpolation

    An interpolating function of n variables with m-dimensional values
    is defined by an (n+m)-dimensional array of values and n
    one-dimensional arrays that define the variables values
    corresponding to the grid points. The grid does not have to be
    equidistant.

    Constructor: InterpolatingFunction(|axes|, |values|, |default|=None)

    Arguments:

    |axes| -- a sequence of one-dimensional arrays, one for each
              variable, specifying the values of the variables at
              the grid points

    |values| -- an array containing the function values on the grid

    |default| -- the value of the function outside the grid. A value
                 of 'None' means that the function is undefined outside
                 the grid and that any attempt to evaluate it there
                 yields an exception.

    Evaluation: 'function(x1, x2, ...)' yields the function value
                obtained by linear interpolation.

    Indexing: all array indexing operations except for the
              NexAxis operator are supported.
    """

    def __init__(self, axes, values, default = None):
        if len(axes) > len(values.shape):
            raise ValueError('Inconsistent arguments')
        self.axes = list(axes)
        self.values = values
        self.default = default
        self.shape = ()
        for axis in self.axes:
            self.shape = self.shape + axis.shape

    def __call__(self, *points):
        if len(points) != len(self.axes):
            raise TypeError('Wrong number of arguments')
        try:
            neighbours = map(_lookup, points, self.axes)
        except ValueError, text:
            if self.default is not None:
                return self.default
            else:
                raise ValueError(text)
        slices = ()
        for item in neighbours:
            slices = slices + index_expression[item[0]:item[1]+1:1]
        values = self.values[slices]
        for item in neighbours:
            values = (1.-item[2])*values[0]+item[2]*values[1]
        return values

    def __len__(self):
        return len(self.axes[0])

    def __getitem__(self, i):
        ti = type(i)
        if ti == type(0):
            if len(self.axes) == 1:
                return (self.axes[0][i], self.values[i])
            else:
                return self._constructor(self.axes[1:], self.values[i])
        elif ti == type(slice(None)):
            axes = [self.axes[0][i]] + self.axes[1:]
            return self._constructor(axes, self.values[i])
        elif ti == type(()):
            axes = []
            rest = self.axes[:]
            for item in i:
                if type(item) != type(0):
                    axes.append(rest[0][item])
                del rest[0]
            axes = axes + rest
            return self._constructor(axes, self.values[i])
        else:
            raise TypeError("illegal index type")

    def __getslice__(self, i, j):
        axes = [self.axes[0][i:j]] + self.axes[1:]
        return self._constructor(axes, self.values[i:j])

    def __getattr__(self, attr):
        if attr == 'real':
            values = self.values
            try:
                values = values.real
            except ValueError:
                pass
            default = self.default
            try:
                default = default.real
            except:
                pass
            return self._constructor(self.axes, values, default)
        elif attr == 'imag':
            try:
                values = self.values.imag
            except ValueError:
                values = 0*self.values
            default = self.default
            try:
                default = self.default.imag
            except:
                try:
                    default = 0*self.default
                except:
                    default = None
            return self._constructor(self.axes, values, default)
        else:
            raise AttributeError(attr)

    def selectInterval(self, first, last, variable=0):
        """Returns a new InterpolatingFunction whose grid is restricted
        to the interval from |first| to |last| along the variable
        whose number is |variable|.
        """
        x = self.axes[variable]
        c = Numeric.logical_and(Numeric.greater_equal(x, first),
                                Numeric.less_equal(x, last))
        i_axes = self.axes[:variable] + [Numeric.compress(c, x)] + \
                 self.axes[variable+1:]
        i_values = Numeric.compress(c, self.values, variable)
        return self._constructor(i_axes, i_values, None)
        
    def derivative(self, variable = 0):
        """Returns a new InterpolatingFunction describing the derivative
        with respect to |variable| (an integer).
        """
        diffaxis = self.axes[variable]
        ui = variable*index_expression[::] + \
             index_expression[1::] + index_expression[...]
        li = variable*index_expression[::] + \
             index_expression[:-1:] + index_expression[...]
        ai = index_expression[::] + \
             (len(self.values.shape)-variable-1) * index_expression[Numeric.NewAxis]
        d_values = (self.values[ui]-self.values[li]) / \
                   (diffaxis[1:]-diffaxis[:-1])[ai]
        diffaxis = 0.5*(diffaxis[1:]+diffaxis[:-1])
        d_axes = self.axes[:variable]+[diffaxis]+self.axes[variable+1:]
        d_default = None
        if self.default is not None:
            d_default = 0.
        return self._constructor(d_axes, d_values, d_default)

    def integral(self, variable = 0):
        """Returns a new InterpolatingFunction describing the integral
        with respect to |variable| (an integer). The integration constant
        is defined in such a way that the value of the integral at the
        first grid point along |variable| is zero."""
        intaxis = self.axes[variable]
        ui = variable*index_expression[::] + \
             index_expression[1::] + index_expression[...]
        li = variable*index_expression[::] + \
             index_expression[:-1:] + index_expression[...]
        uai = index_expression[1::] + (len(self.values.shape)-variable-1) * \
              index_expression[Numeric.NewAxis]
        lai = index_expression[:-1:] + (len(self.values.shape)-variable-1) * \
              index_expression[Numeric.NewAxis]
        i_values = 0.5*Numeric.add.accumulate((self.values[ui]
                                               +self.values[li])* \
                                              (intaxis[uai]-intaxis[lai]),
                                              variable)
        s = list(self.values.shape)
        s[variable] = 1
        z = Numeric.zeros(tuple(s))
        return self._constructor(self.axes,
                                 Numeric.concatenate((z, i_values), variable),
                                 None)

    def definiteIntegral(self, variable = 0):
        """Returns a new InterpolatingFunction describing the definite integral
        with respect to |variable| (an integer). The integration constant
        is defined in such a way that the value of the integral at the
        first grid point along |variable| is zero. In the case of a
        function of one variable, the definite integral is a number."""
        intaxis = self.axes[variable]
        ui = variable*index_expression[::] + \
             index_expression[1::] + index_expression[...]
        li = variable*index_expression[::] + \
             index_expression[:-1:] + index_expression[...]
        uai = index_expression[1::] + (len(self.values.shape)-variable-1) * \
              index_expression[Numeric.NewAxis]
        lai = index_expression[:-1:] + (len(self.values.shape)-variable-1) * \
              index_expression[Numeric.NewAxis]
        i_values = 0.5*Numeric.add.reduce((self.values[ui]+self.values[li]) * \
                   (intaxis[uai]-intaxis[lai]), variable)
        if len(self.axes) == 1:
            return i_values
        else:
            i_axes = self.axes[:variable] + self.axes[variable+1:]
            return self._constructor(i_axes, i_values, None)

    def fitPolynomial(self, order):
        """Returns a polynomial of |order| with parameters obtained from
        a least-squares fit to the grid values."""
        points = _combinations(self.axes)
        return Polynomial.fitPolynomial(order, points,
                                        Numeric.ravel(self.values))

    def __abs__(self):
        values = abs(self.values)
        try:
            default = abs(self.default)
        except:
            default = self.default
        return self._constructor(self.axes, values, default)

    def _mathfunc(self, function):
        if self.default is None:
            default = None
        else:
            default = function(self.default)
        return self._constructor(self.axes, function(self.values), default)

    def exp(self):
        return self._mathfunc(Numeric.exp)

    def log(self):
        return self._mathfunc(Numeric.log)

    def sqrt(self):
        return self._mathfunc(Numeric.sqrt)

    def sin(self):
        return self._mathfunc(Numeric.sin)

    def cos(self):
        return self._mathfunc(Numeric.cos)

    def tan(self):
        return self._mathfunc(Numeric.tan)

    def sinh(self):
        return self._mathfunc(Numeric.sinh)

    def cosh(self):
        return self._mathfunc(Numeric.cosh)

    def tanh(self):
        return self._mathfunc(Numeric.tanh)

    def arcsin(self):
        return self._mathfunc(Numeric.arcsin)

    def arccos(self):
        return self._mathfunc(Numeric.arccos)

    def arctan(self):
        return self._mathfunc(Numeric.arctan)

InterpolatingFunction._constructor = InterpolatingFunction

#
# Interpolating function on data in netCDF file
#
class NetCDFInterpolatingFunction(InterpolatingFunction):

    """Function defined by values on a grid in a netCDF file

    A subclass of InterpolatingFunction.

    Constructor: NetCDFInterpolatingFunction(|filename|, |axesnames|,
                                             |variablename|,
                                             |default|=None)

    Arguments:

    |filename| -- the name of the netCDF file

    |axesnames| -- the names of the netCDF variables that contain the
                   axes information

    |variablename| -- the name of the netCDF variable that contains
                      the data values

    |default| -- the value of the function outside the grid. A value
                 of 'None' means that the function is undefined outside
                 the grid and that any attempt to evaluate it there
                 yields an exception.

    Evaluation: 'function(x1, x2, ...)' yields the function value
                obtained by linear interpolation.
    """

    def __init__(self, filename, axesnames, variablename, default = None):
        from Scientific.IO.NetCDF import NetCDFFile
        self.file = NetCDFFile(filename, 'r')
        self.axes = map(lambda n, f=self.file: f.variables[n], axesnames)
        self.values = self.file.variables[variablename]
        self.default = default
        self.shape = ()
        for axis in self.axes:
            self.shape = self.shape + axis.shape

NetCDFInterpolatingFunction._constructor = InterpolatingFunction


# Helper functions

def _lookup(point, axis):
    j = Numeric.int_sum(Numeric.less_equal(axis, point))
    if j == len(axis):
        if point == axis[j-1]:
            return j-2, j-1, 1.
        else:
            j = 0
    if j == 0:
        raise ValueError('Point outside grid of values')
    i = j-1
    weight = (point-axis[i])/(axis[j]-axis[i])
    return i, j, weight

def _combinations(axes):
    if len(axes) == 1:
        return map(lambda x: (x,), axes[0])
    else:
        rest = _combinations(axes[1:])
        l = []
        for x in axes[0]:
            for y in rest:
                l.append((x,)+y)
        return l


# Test code

if __name__ == '__main__':

    from Numeric import *
    axis = arange(0,1.1,0.1)
    values = sqrt(axis)
    s = InterpolatingFunction((axis,), values)
    print s(0.22), sqrt(0.22)
    sd = s.derivative()
    print sd(0.35), 0.5/sqrt(0.35)
    si = s.integral()
    print si(0.42), (0.42**1.5)/1.5
    print s.definiteIntegral()
    values = sin(axis[:,NewAxis])*cos(axis)
    sc = InterpolatingFunction((axis,axis),values)
    print sc(0.23, 0.77), sin(0.23)*cos(0.77)
