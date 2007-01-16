# This module provides interpolation for functions defined on a grid.
#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 2007-1-16
#

"""
Interpolation of functions defined on a grid
"""

from Scientific import N; Numeric = N
import Polynomial
from Scientific.indexing import index_expression
import operator

#
# General interpolating functions.
#
class InterpolatingFunction:

    """X{Function} defined by values on a X{grid} using X{interpolation}

    An interpolating function of M{n} variables with M{m}-dimensional values
    is defined by an M{(n+m)}-dimensional array of values and M{n}
    one-dimensional arrays that define the variables values
    corresponding to the grid points. The grid does not have to be
    equidistant.

    An InterpolatingFunction object has attributes C{real} and C{imag}
    like a complex function (even if its values are real).
    """

    def __init__(self, axes, values, default = None):
        """
        @param axes: a sequence of one-dimensional arrays, one for each
            variable, specifying the values of the variables at
            the grid points
        @type axes: sequence of Numeric.array

        @param values: the function values on the grid
        @type values: Numeric.array

        @param default: the value of the function outside the grid. A value
            of C{None} means that the function is undefined outside
            the grid and that any attempt to evaluate it there
            raises an exception.
        @type default: number or C{None}
        """
        if len(axes) > len(values.shape):
            raise ValueError('Inconsistent arguments')
        self.axes = list(axes)
        self.values = values
        self.default = default
        self.shape = ()
        for axis in self.axes:
            self.shape = self.shape + axis.shape

    def __call__(self, *points):
        """
        @returns: the function value obtained by linear interpolation
        @rtype: number
        @raise TypeError: if the number of arguments (C{len(points)})
            does not match the number of variables of the function
        @raise ValueError: if the evaluation point is outside of the
            domain of definition and no default value is defined
        """
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
        """
        @returns: number of variables
        @rtype: C{int}
        """
        return len(self.axes[0])

    def __getitem__(self, i):
        """
        @param i: any indexing expression possible for C{Numeric.array}
            that does not use C{Numeric.NewAxis}
        @type i: indexing expression
        @returns: an InterpolatingFunction whose number of variables
            is reduced, or a number if no variable is left
        @rtype: L{InterpolatingFunction} or number
        @raise TypeError: if i is not an allowed index expression
        """
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
        """
        @param i: lower slice index
        @type i: C{int}
        @param j: upper slice index
        @type j: C{int}
        @returns: an InterpolatingFunction whose number of variables
            is reduced by one, or a number if no variable is left
        @rtype: L{InterpolatingFunction} or number
        """
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
        """
        @param first: lower limit of an axis interval
        @type first: C{float}
        @param last: upper limit of an axis interval
        @type last: C{float}
        @param variable: the index of the variable of the function
            along which the interval restriction is applied
        @type variable: C{int}
        @returns: a new InterpolatingFunction whose grid is restricted
        @rtype: L{InterpolatingFunction}
        """
        x = self.axes[variable]
        c = Numeric.logical_and(Numeric.greater_equal(x, first),
                                Numeric.less_equal(x, last))
        i_axes = self.axes[:variable] + [Numeric.compress(c, x)] + \
                 self.axes[variable+1:]
        i_values = Numeric.compress(c, self.values, variable)
        return self._constructor(i_axes, i_values, None)
        
    def derivative(self, variable = 0):
        """
        @param variable: the index of the variable of the function
            with respect to which the X{derivative} is taken
        @type variable: C{int}
        @returns: a new InterpolatingFunction containing the numerical
            derivative
        @rtype: L{InterpolatingFunction}
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
        """
        @param variable: the index of the variable of the function
            with respect to which the X{integration} is performed
        @type variable: C{int}
        @returns: a new InterpolatingFunction containing the numerical
            X{integral}. The integration constant is defined such that
            the integral at the first grid point is zero.
        @rtype: L{InterpolatingFunction}
        """
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
        """
        @param variable: the index of the variable of the function
            with respect to which the X{integration} is performed
        @type variable: C{int}
        @returns: a new InterpolatingFunction containing the numerical
            X{integral}. The integration constant is defined such that
            the integral at the first grid point is zero. If the original
            function has only one free variable, the definite integral
            is a number
        @rtype: L{InterpolatingFunction} or number
        """
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
        """
        @param order: the order of the X{polynomial} to be fitted
        @type order: C{int}
        @returns: a polynomial whose coefficients have been obtained
            by a X{least-squares} fit to the grid values
        @rtype: L{Scientific.Functions.Polynomial}
        """
        points = _combinations(self.axes)
        return Polynomial._fitPolynomial(order, points,
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

    """Function defined by values on a grid in a X{netCDF} file

    A subclass of L{InterpolatingFunction}.
    """

    def __init__(self, filename, axesnames, variablename, default = None):
        """
        @param filename: the name of the netCDF file
        @type filename: C{str}

        @param axesnames: the names of the netCDF variables that contain the
            axes information
        @type axes: sequence of C{str}

        @param variablename: the name of the netCDF variable that contains
            the data values
        @type variablename: C{str}

        @param default: the value of the function outside the grid. A value
            of C{None} means that the function is undefined outside
            the grid and that any attempt to evaluate it there
            raises an exception.
        @type default: number or C{None}
        """
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
        if Numeric.fabs(point - axis[j-1]) < 1.e-9:
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
