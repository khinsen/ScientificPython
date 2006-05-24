# This module provides a class representing scalar, vector, and tensor fields.
#
# Written by Konrad Hinsen <khinsen@cea.fr>
# last revision: 2005-9-5
#


from Scientific import N; Numeric = N
from Scientific.Geometry import Vector, Tensor
from Scientific.indexing import index_expression
from Scientific.Functions import Interpolation

#
# General tensor field base class
#
class TensorField(Interpolation.InterpolatingFunction):

    """Tensor field of arbitrary rank

    A tensor field is described by a tensor at each point of
    a three-dimensional rectangular grid. The grid spacing
    may be non-uniform. Tensor fields are implemented as a subclass
    of InterpolatingFunction from the module
    Scientific.Functions.Interpolation and thus share all methods
    defined in that class.

    Constructor: TensorField(|rank|, |axes|, |values|, |default|='None')

    Arguments:

    |rank| -- a non-negative integer indicating the tensor rank

    |axes| -- a sequence of three one-dimensional arrays, each
              of which specifies one coordinate (x, y, z) of the
              grid points

    |values| -- an array of 'rank+3' dimensions. Its first
                three dimensions correspond to the x, y, z
                directions and must have lengths compatible with
                the axis arrays. The remaining dimensions must
                have length 3.

    |default| -- the value of the field for points outside the grid.
                 A value of 'None' means that an exception will be
                 raised for an attempt to evaluate the field outside
                 the grid. Any other value must a tensor of the
                 correct rank.
                 
    Evaluation:

    - 'tensorfield(x, y, z)'   (three coordinates)
    - 'tensorfield(coordinates)'  (any sequence containing three coordinates)
    """

    def __init__(self, rank, axes, values, default = None, check = 1):
        if check:
            if len(axes) != 3:
                raise ValueError('Field must have three axes')
            if len(values.shape) != 3 + rank:
                raise ValueError('Values must have rank ' + `rank`)
            if values.shape[3:] != rank*(3,):
                raise ValueError('Values must have dimension 3')
        self.rank = rank
        self.spacing = []
        for axis in axes:
            d = axis[1:]-axis[:-1]
            self.spacing.append(d[0])
            if check:
                dmin = Numeric.minimum.reduce(d)
                if abs(dmin-Numeric.maximum.reduce(d)) > 0.0001*dmin:
                    raise ValueError('Grid must be equidistant')
        Interpolation.InterpolatingFunction.__init__(self, axes, values,
                                                     default)

    def __call__(self, *points):
        if len(points) == 1:
            points = tuple(points[0])
        value = apply(Interpolation.InterpolatingFunction.__call__,
                      (self, ) + points)
        if self.rank == 0:
            return value
        elif self.rank == 1:
            return Vector(value)
        else:
            return Tensor(value)

    def __getitem__(self, index):
        if type(index) == type(0):
            index = (index,)
        rank = self.rank - len(index)
        if rank < 0:
            raise ValueError('Number of indices too large')
        index = index_expression[...] + index + rank*index_expression[::]
        try: default = self.default[index]
        except TypeError: default = None
        if rank == 0:
            return ScalarField(self.axes, self.values[index], default, 0)
        elif rank == 1:
            return VectorField(self.axes, self.values[index], default, 0)
        else:
            return TensorField(self.axes, rank, self.values[index], default, 0)

    def zero(self):
        "Returns a tensor of the correct rank with zero elements."
        if self.rank == 0:
            return 0.
        else:
            return Tensor(Numeric.zeros(self.rank*(3,), Numeric.Float))

    def derivative(self, variable):
        """Returns the derivative with respect to |variable|, which
        must be one of 0, 1, or 2."""
        ui = variable*index_expression[::] + \
             index_expression[2::] + index_expression[...]
        li = variable*index_expression[::] + \
             index_expression[:-2:] + index_expression[...]
        d_values = 0.5*(self.values[ui]-self.values[li])/self.spacing[variable]
        diffaxis = self.axes[variable]
        diffaxis = 0.5*(diffaxis[2:]+diffaxis[:-2])
        d_axes = self.axes[:variable]+[diffaxis]+self.axes[variable+1:]
        d_default = None
        if self.default is not None:
            d_default = Numeric.zeros(self.rank*(3,), Numeric.Float)
        return self._constructor(d_axes, d_values, d_default, 0)

    def allDerivatives(self):
        "Returns all three derivatives (x, y, z)."
        x = self.derivative(0)
        x._reduceAxis(1)
        x._reduceAxis(2)
        y = self.derivative(1)
        y._reduceAxis(0)
        y._reduceAxis(2)
        z = self.derivative(2)
        z._reduceAxis(0)
        z._reduceAxis(1)
        return x, y, z

    def _reduceAxis(self, variable):
        self.axes[variable] = self.axes[variable][1:-1]
        i = variable*index_expression[::] + \
            index_expression[1:-1:] + index_expression[...]
        self.values = self.values[i]

    def _checkCompatibility(self, other):
        pass

    def __add__(self, other):
        self._checkCompatibility(other)
        if self.default is None or other.default is None:
            default = None
        else:
            default = self.default + other.default
        return self._constructor(self.axes, self.values+other.values,
                                 default, 0)

    def __sub__(self, other):
        self._checkCompatibility(other)
        if self.default is None or other.default is None:
            default = None
        else:
            default = self.default - other.default
        return self._constructor(self.axes, self.values-other.values,
                                 default, 0)

#
# Scalar field class definition
#
class ScalarField(TensorField):

    """Scalar field (tensor field of rank 0)

    Constructor: ScalarField(|axes|, |values|, |default|='None')

    A subclass of TensorField.
    """

    def __init__(self, axes, values, default = None, check = 1):
        TensorField.__init__(self, 0, axes, values, default, check)

    def gradient(self):
        "Returns the gradient (a vector field)."
        x, y, z = self.allDerivatives()
        grad = Numeric.transpose(Numeric.array([x.values, y.values, z.values]),
                                 [1,2,3,0])
        if self.default is None:
            default = None
        else:
            default = Numeric.zeros((3,), Numeric.Float)
        return VectorField(x.axes, grad, default, 0)

    def laplacian(self):
        "Returns the laplacian (a scalar field)."
        return self.gradient().divergence()

ScalarField._constructor = ScalarField

#
# Vector field class definition
#
class VectorField(TensorField):

    """Vector field (tensor field of rank 1)

    Constructor: VectorField(|axes|, |values|, |default|='None')

    A subclass of TensorField.
    """

    def __init__(self, axes, values, default = None, check = 1):
        TensorField.__init__(self, 1, axes, values, default, check)

    def zero(self):
        return Vector(0., 0., 0.)

    def _divergence(self, x, y, z):
        return x[0] + y[1] + z[2]

    def _curl(self, x, y, z):
        curl_x = y.values[..., 2] - z.values[..., 1]
        curl_y = z.values[..., 0] - x.values[..., 2]
        curl_z = x.values[..., 1] - y.values[..., 0]
        curl = Numeric.transpose(Numeric.array([curl_x, curl_y, curl_z]),
                                 [1,2,3,0])
        if self.default is None:
            default = None
        else:
            default = Numeric.zeros((3,), Numeric.Float)
        return VectorField(x.axes, curl, default, 0)

    def _strain(self, x, y, z):
        strain = Numeric.transpose(Numeric.array([x.values, y.values,
                                                  z.values]), [1,2,3,0,4])
        strain = 0.5*(strain+Numeric.transpose(strain, [0,1,2,4,3]))
        trace = (strain[..., 0,0] + strain[..., 1,1] + strain[..., 2,2])/3.
        strain = strain - trace[..., Numeric.NewAxis, Numeric.NewAxis] * \
                 Numeric.identity(3)[Numeric.NewAxis, Numeric.NewAxis,
                                     Numeric.NewAxis, :, :]
        if self.default is None:
            default = None
        else:
            default = Numeric.zeros((3, 3), Numeric.Float)
        return TensorField(2, x.axes, strain, default, 0)
        
    def divergence(self):
        "Returns the divergence (a scalar field)."
        x, y, z = self.allDerivatives()
        return self._divergence(x, y, z)

    def curl(self):
        "Returns the curl (a vector field)."
        x, y, z = self.allDerivatives()
        return self._curl(x, y, z)

    def strain(self):
        "Returns the strain (a tensor field of rank 2)."
        x, y, z = self.allDerivatives()
        return self._strain(x, y, z)

    def divergenceCurlAndStrain(self):
        "Returns all derivative fields: divergence, curl, and strain."
        x, y, z = self.allDerivatives()
        return self._divergence(x, y, z), self._curl(x, y, z), \
               self._strain(x, y, z)

    def laplacian(self):
        "Returns the laplacian (a vector field)."
        x, y, z = self.allDerivatives()
        return self._divergence(x, y, z).gradient()-self._curl(x, y, z).curl()

    def length(self):
        """Returns a scalar field corresponding to the length (norm) of
        the vector field."""
        l = Numeric.sqrt(Numeric.add.reduce(self.values**2, -1))
        try: default = Numeric.sqrt(Numeric.add.reduce(self.default))
        except ValueError: default = None
        return ScalarField(self.axes, l, default, 0)

VectorField._constructor = VectorField

# Sort indices for automatic document string extraction
TensorField._documentation_sort_index = 0
ScalarField._documentation_sort_index = 1
VectorField._documentation_sort_index = 2

#
# Test code
#
if __name__ == '__main__':

    from Numeric import *
    axis = arange(0., 1., 0.1)
    values = zeros((10,10,10,3), Float)
    zero = VectorField(3*(axis,), values)
    div = zero.divergence()
    curl = zero.curl()
    strain = zero.strain()
