# This module defines a multivariate polynomial class
#
# Written by Konrad Hinsen <khinsen@cea.fr>
# last revision: 2005-9-5
#

from Scientific import N, LA; Numeric = N; LinearAlgebra = LA
from Scientific.indexing import index_expression

# Class definition

class Polynomial:

    """Multivariate polynomial

    Instances of this class represent polynomials of any order and
    in any number of variables. They can be evaluated like functions.

    Constructor: Polynomial(|coefficients|), where |coefficients| is
    an array whose dimension defines the number of variables and whose
    length along each axis defines the order in the corresponding
    variable. The coefficients are ordered according to increasing
    powers, i.e.\ [1., 2.] stands for 1.+2.*x.
    """

    def __init__(self, coefficients):
        self.coeff = Numeric.array(coefficients)
        self.dim = len(self.coeff.shape)

    is_polynomial = 1

    def __call__(self, *args):
        if len(args) != self.dim:
            raise TypeError('Wrong number of arguments')
        p = _powers(args, self.coeff.shape)
        return Numeric.add.reduce(Numeric.ravel(p*self.coeff))

    def __repr__(self):
        if self.dim == 1:
            return "Polynomial(%s)" % repr(list(self.coeff))
        else:
            return "Polynomial(%s)" % repr(self.coeff)

    def __coerce__(self, other):
        if hasattr(other, 'is_polynomial'):
            return (self, other)
        elif hasattr(other, 'is_rational_function'):
            return None
        else:
            return (self, Polynomial([other]))

    def __add__(self, other):
        dim = max(self.dim, other.dim)
        shape = Numeric.zeros((dim,), Numeric.Int)
        shape[:self.dim] = self.coeff.shape
        shape[:other.dim] = Numeric.maximum(shape[:other.dim],
                                            other.coeff.shape)
        coeff1 = Numeric.zeros(shape, self.coeff.typecode())
        index = tuple(map(lambda d: slice(0, d), self.coeff.shape) + \
                      (dim-self.dim)*[0])
        coeff1[index] = self.coeff
        coeff2 = Numeric.zeros(shape, other.coeff.typecode())
        index = tuple(map(lambda d: slice(0, d), other.coeff.shape) + \
                      (dim-other.dim)*[0])
        coeff2[index] = other.coeff
        return Polynomial(coeff1+coeff2)

    def __mul__(self, other):
        if self.dim != 1 or other.dim != 1:
            raise ValueError("not implemented")
        c = Numeric.multiply.outer(self.coeff, other.coeff)
        temp = Numeric.concatenate((c, Numeric.zeros(2*(c.shape[0],))), 1)
        temp = Numeric.ravel(temp)[:-c.shape[0]]
        temp.shape = (c.shape[0], c.shape[0]+c.shape[1]-1)
        return Polynomial(Numeric.sum(temp))

    def __div__(self, other):
        if self.dim != 1 or other.dim != 1:
            raise ValueError("not implemented")
        if len(other.coeff) == 1:
            return Polynomial(self.coeff/other.coeff[0])
        from Rational import RationalFunction
        return RationalFunction(self, other)

    def __rdiv__(self, other):
        from Rational import RationalFunction
        return RationalFunction(other, self)

    def derivative(self, variable=0):
        "Returns the derivative with respect to |variable|."
        n = self.coeff.shape[variable]
        if n == 1:
            return Polynomial(apply(Numeric.zeros, self.dim*(1,)))
        index = variable*index_expression[::] + \
                index_expression[1::] + index_expression[...]
        factor = Numeric.arange(1.,n)
        factor = factor[index_expression[::] +
                        (self.dim-variable-1) * \
                        index_expression[Numeric.NewAxis]]
        return Polynomial(factor*self.coeff[index])

    def integral(self, variable=0):
        "Returns the indefinite integral with respect to |variable|."
        n = self.coeff.shape[variable]
        factor = 1./Numeric.arange(1.,n+1)
        factor = factor[index_expression[::] +
                        (self.dim-variable-1) * \
                        index_expression[Numeric.NewAxis]]
        s = map(None, self.coeff.shape)
        s[variable] = 1
        z = apply(Numeric.zeros, tuple(s))
        intcoeff = Numeric.concatenate((z, factor*self.coeff), variable)
        return Polynomial(intcoeff)

    def zeros(self):
        "Returns an array containing the zeros (one variable only)."
        if self.dim != 1:
            raise ValueError("not implemented")
        n = len(self.coeff)-1
        if n == 0:
            return Numeric.array([])
        a = Numeric.zeros((n, n), self.coeff.typecode())
        if n > 1:
            a[1:, :-1] = Numeric.identity(n-1)
        a[:, -1] = -self.coeff[:-1]/self.coeff[-1]
        from LinearAlgebra import eigenvalues
        return eigenvalues(a)

# Polynomial fit constructor

def fitPolynomial(order, points, values):
    if len(points) != len(values):
        raise ValueError('Inconsistent arguments')
    if type(order) != type(()):
        order = (order,)
    order = tuple(map(lambda n: n+1, order))
    if not _isSequence(points[0]):
        points = map(lambda p: (p,), points)
    if len(order) != len(points[0]):
        raise ValueError('Inconsistent arguments')
    if Numeric.multiply.reduce(order) > len(points):
        raise ValueError('Not enough points')
    matrix = []
    for p in points:
        matrix.append(Numeric.ravel(_powers(p, order)))
    matrix = Numeric.array(matrix)
    values = Numeric.array(values)
    inv = LinearAlgebra.generalized_inverse(matrix)
    coeff = Numeric.dot(inv, values)
    #coeff = LinearAlgebra.linear_least_squares(matrix, values)[0]
    coeff = Numeric.reshape(coeff, order)
    return Polynomial(coeff)

# Helper functions

def _powers(x, n):
    p = 1.
    index = index_expression[::] + \
            (len(x)-1)*index_expression[Numeric.NewAxis]
    for i in range(len(x)):
        pi = Numeric.multiply.accumulate(Numeric.array([1.]+(n[i]-1)*[x[i]]))
        p = p*pi[index]
        index = index[-1:] + index[:-1]
    return p

def _isSequence(object):
    n = -1
    try: n = len(object)
    except: pass
    return n >= 0

# Test code

if __name__ == '__main__':

    p1 = Polynomial([1.,0.3,1.,-0.4])
    x = -1.9
    print p1(x), ((-0.4*x+1.)*x+0.3)*x+1.
    zeros = p1.zeros()
    for z in zeros:
        print z, p1(z)
    p2 = Polynomial([[1.,0.3],[-0.2,0.5]])
    y = 0.3
    print p2(x,y), 1. + 0.3*y - 0.2*x + 0.5*x*y
    fit = fitPolynomial(2, [1.,2.,3.,4.], [2.,4.,8.,14.])
    print fit.coeff


