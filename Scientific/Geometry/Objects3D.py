# This module defines some geometrical objects in 3D-space.
#
# Written by Konrad Hinsen <khinsen@cea.fr>
# last revision: 2005-9-5
#

from Scientific.Geometry import Vector
from Scientific import N; Numeric = N


# Small number
_eps = 1.e-16

#
# The base class
#
class GeometricalObject3D:

    """Geometrical object in 3D space

    This is an abstract base class; to create instances, use one of
    the subclasses.
    """
 
    def intersectWith(self, other):
        """Returns the geometrical object that results from the
        intersection with |other|. If there is no intersection,
        the result is 'None'.

        Note that intersection is not implemented for all possible
        pairs of objects. A 'ValueError' is raised for combinations
        that haven't been implemented yet."""
        if self.__class__ > other.__class__:
            self, other = other, self
        try:
            f, switch = _intersectTable[(self.__class__, other.__class__)]
            if switch:
                return f(other, self)
            else:
                return f(self, other)
        except KeyError:
            raise ValueError("Can't calculate intersection of " +
                             self.__class__.__name__ + " with " +
                             other.__class__.__name__)

    def hasPoint(self, point):
        "Returns 1 if |point| is in the object."
        return self.distanceFrom(point) < _eps

    def distanceFrom(self, point):
        "Returns the distance of |point| from the closest point of the object."
        raise ValueError("not yet implemented")

    def volume(self):
        """Returns the volume. The result is 'None' for unbounded objects
        and zero for lower-dimensional objects."""
        raise ValueError("not yet implemented")

_intersectTable = {}

#
# Spheres
#
class Sphere(GeometricalObject3D):

    """Sphere

    A subclass of GeometricalObject3D.
    
    Constructor: Sphere(|center|, |radius|), where |center| is a vector and
    |radius| a float.
    """

    def __init__(self, center, radius):
        self.center = center
        self.radius = radius

    def volume(self):
        return (4.*Numeric.pi/3.) * self.radius**3

    def distanceFrom(self, point):
        d = (point-self.center).length() - self.radius
        if d < 0.:
            return 0.
        else:
            return d

#
# Planes
#
class Plane(GeometricalObject3D):

    """Plane

    A subclass of GeometricalObject3D.
    
    Constructor:

    - Plane(|point|, |normal|), where |point| (a vector) is an arbitrary
      point in the plane and |normal| (a vector) indicated the direction
      normal to the plane.

    - Plane(|p1|, |p2|, |p3|), where each argument is a vector and describes
      a point in the plane. The three points may not be colinear.
    """

    def __init__(self, *args):
        if len(args) == 2:   # point, normal
            self.normal = args[1].normal()
            self.distance_from_zero = self.normal*args[0]
        else:                # three points
            v1 = args[1]-args[0]
            v2 = args[2]-args[1]
            self.normal = (v1.cross(v2)).normal()
            self.distance_from_zero = self.normal*args[1]

    def distanceFrom(self, point):
        return abs(self.normal*point-self.distance_from_zero)

    def projectionOf(self, point):
        "Returns the projection of |point| onto the plane."
        distance = self.normal*point-self.distance_from_zero
        return point - distance*self.normal

    def rotate(self, axis, angle):
        "Returns a copy of the plane rotated around the coordinate origin."
        point = rotatePoint(self.distance_from_zero*self.normal, axis, angle)
        normal = rotateDirection(self.normal, axis, angle)
        return Plane(point, normal)

    def volume(self):
        return 0.

#
# Infinite cones
#
class Cone(GeometricalObject3D):

    """Cone

    A subclass of GeometricalObject3D.
    
    Constructor: Cone(|tip|, |axis|, |angle|), where |tip| is a vector
    indicating the location of the tip, |axis| is a vector that
    describes the direction of the line of symmetry, and |angle| is
    the angle between the line of symmetry and the cone surface.
    """

    def __init__(self, center, axis, angle):
        self.center = center
        self.axis = axis.normal()
        self.angle = angle

    def volume(self):
        return None

#
# Circles
#
class Circle(GeometricalObject3D):

    """Circle

    A subclass of GeometricalObject3D.
    
    Constructor: Circle(|center|, |normal|, |radius|), where |center|
    is a vector indicating the center of the circle, |normal| is a
    vector describing the direction normal to the plane of the circle,
    and |radius| is a float.
    """

    def __init__(self, center, normal, radius):
        self.center = center
        self.normal = normal
        self.radius = radius

    def volume(self):
        return 0.

#
# Lines
#
class Line(GeometricalObject3D):

    """Line

    A subclass of GeometricalObject3D.
    
    Constructor: Line(|point|, |direction|), where |point| is a vector
    indicating any point on the line and |direction| is a vector
    describing the direction of the line.
    """

    def __init__(self, point, direction):
        self.point = point
        self.direction = direction.normal()

    def distanceFrom(self, point):
        d = self.point-point
        d = d - (d*self.direction)*self.direction
        return d.length()

    def projectionOf(self, point):
        "Returns the projection of |point| onto the line."
        d = self.point-point
        d = d - (d*self.direction)*self.direction
        return point+d

    def volume(self):
        return 0.

#
# Intersection calculations
#
def _addIntersectFunction(f, class1, class2):
    switch = class1 > class2
    if switch:
        class1, class2 = class2, class1
    _intersectTable[(class1, class2)] = (f, switch)

# Sphere with sphere

def _intersectSphereSphere(sphere1, sphere2):
    r1r2 = sphere2.center-sphere1.center
    d = r1r2.length()
    if d > sphere1.radius+sphere2.radius:
        return None
    if d+min(sphere1.radius, sphere2.radius) < \
                             max(sphere1.radius, sphere2.radius):
        return None
    x = 0.5*(d**2 + sphere1.radius**2 - sphere2.radius**2)/d
    h = Numeric.sqrt(sphere1.radius**2-x**2)
    normal = r1r2.normal()
    return Circle(sphere1.center + x*normal, normal, h)

_addIntersectFunction(_intersectSphereSphere, Sphere, Sphere)

# Sphere with cone

def _intersectSphereCone(sphere, cone):
    if sphere.center != cone.center:
        raise ValueError("Not yet implemented")
    from_center = sphere.radius*Numeric.cos(cone.angle)
    radius = sphere.radius*Numeric.sin(cone.angle)
    return Circle(cone.center+from_center*cone.axis, cone.axis, radius)

_addIntersectFunction(_intersectSphereCone, Sphere, Cone)

# Plane with plane

def _intersectPlanePlane(plane1, plane2):
    if abs(abs(plane1.normal*plane2.normal)-1.) < _eps:
        if abs(plane1.distance_from_zero-plane2.distance_from_zero) < _eps:
            return plane1
        else:
            return None
    else:
        direction = plane1.normal.cross(plane2.normal)
        point_in_1 = plane1.distance_from_zero*plane1.normal
        point_in_both = point_in_1 - (point_in_1*plane2.normal -
                                      plane2.distance_from_zero)*plane2.normal
        return Line(point_in_both, direction)

_addIntersectFunction(_intersectPlanePlane, Plane, Plane)

# Circle with plane

def _intersectCirclePlane(circle, plane):
    if abs(abs(circle.normal*plane.normal)-1.) < _eps:
        if plane.hasPoint(circle.center):
            return circle
        else:
            return None
    else:
        line = plane.intersectWith(Plane(circle.center, circle.normal))
        x = line.distanceFrom(circle.center)
        if x > circle.radius:
            return None
        else:
            angle = Numeric.arccos(x/circle.radius)
            along_line = Numeric.sin(angle)*circle.radius
            normal = circle.normal.cross(line.direction)
            if line.distanceFrom(circle.center+normal) > x:
                normal = -normal
            return (circle.center+x*normal-along_line*line.direction,
                    circle.center+x*normal+along_line*line.direction)
            
_addIntersectFunction(_intersectCirclePlane, Circle, Plane)

#
# Rotation
#
def rotateDirection(vector, axis, angle):
    s = Numeric.sin(angle)
    c = Numeric.cos(angle)
    c1 = 1-c
    axis = axis.direction
    return s*axis.cross(vector) + c1*(axis*vector)*axis + c*vector

def rotatePoint(point, axis, angle):
    return axis.point + rotateDirection(point-axis.point, axis, angle)


#
# Lattices
#

#
# Lattice base class
#
class Lattice:

    def __init__(self, function):
        if function is not None:
            self.elements = map(function, self.elements)

    def __getitem__(self, item):
        return self.elements[item]

    def __setitem__(self, item, value):
        self.elements[item] = value

    def __len__(self):
        return len(self.elements)

#
# General rhombic lattice
#
class RhombicLattice(Lattice):

    """Lattice with rhombic elementary cell

    A lattice object contains values defined on a finite periodic
    structure that is created by replicating a given elementary
    cell along the three lattice vectors. The elementary cell can
    contain any number of points.

    Constructor: RhombicLattice(|elementary_cell|, |lattice_vectors|, |cells|,
                                |function|='None', |base|='None')

    Arguments:

    |elementary_cell| -- a list of the points (vectors) in the elementary cell

    |lattice_vectors| -- a tuple of three vectors describing the edges
                         of the elementary cell

    |cells| -- a tuple of three integers, indicating how often the elementary
               cell should be replicated along each lattice vector

    |function| -- the function to be applied to each point in the lattice
                  in order to obtain the value stored in the lattice.
                  If no function is specified, the point itself becomes
                  the value stored in the lattice.

    |base| -- an offset added to all lattice points
    """

    def __init__(self, elementary_cell, lattice_vectors, cells,
                 function=None, base=None):
        if len(lattice_vectors) != len(cells):
            raise TypeError('Inconsistent dimension specification')
        if base is None:
            base = Vector(0, 0, 0)
        self.dimension = len(lattice_vectors)
        self.elements = []
        self.makeLattice(elementary_cell, lattice_vectors, cells, base)
        Lattice.__init__(self, function)

    def makeLattice(self, elementary_cell, lattice_vectors, cells, base):
        if len(cells) == 0:
            for p in elementary_cell:
                self.elements.append(p+base)
        else:
            for i in range(cells[0]):
                self.makeLattice(elementary_cell, lattice_vectors[1:],
                                 cells[1:], base+i*lattice_vectors[0])
            
#
# Bravais lattice
#
class BravaisLattice(RhombicLattice):

    """General Bravais lattice

    This is a subclass of RhombicLattice, describing the special case
    of an elementary cell containing one point.

    Constructor: BravaisLattice(|lattice_vectors|, |cells|,
                                |function|='None', |base|='None')

    Arguments:

    |lattice_vectors| -- a tuple of three vectors describing the edges
                         of the elementary cell

    |cells| -- a tuple of three integers, indicating how often the elementary
               cell should be replicated along each lattice vector

    |function| -- the function to be applied to each point in the lattice
                  in order to obtain the value stored in the lattice.
                  If no function is specified, the point itself becomes
                  the value stored in the lattice.

    |base| -- an offset added to all lattice points
    """

    def __init__(self, lattice_vectors, cells, function=None, base=None):
        cell = [Vector(0,0,0)]
        RhombicLattice.__init__(self, cell, lattice_vectors, cells,
                                function, base)

#
# Simple cubic lattice
#
class SCLattice(BravaisLattice):

    """Simple cubic lattice

    This is a subclass of BravaisLattice, describing the special case
    of a cubic elementary cell.

    Constructor: SCLattice(|cellsize|, |cells|, |function|='None',
                           |base|='None')

    Arguments:

    |cellsize| -- the edge length of the cubic elementary cell

    |cells| -- a tuple of three integers, indicating how often the elementary
               cell should be replicated along each lattice vector

    |function| -- the function to be applied to each point in the lattice
                  in order to obtain the value stored in the lattice.
                  If no function is specified, the point itself becomes
                  the value stored in the lattice.

    |base| -- an offset added to all lattice points
    """

    def __init__(self, cellsize, cells, function=None, base=None):
        lattice_vectors = (cellsize*Vector(1., 0., 0.),
                           cellsize*Vector(0., 1., 0.),
                           cellsize*Vector(0., 0., 1.))
        if type(cells) != type(()):
            cells = 3*(cells,)
        BravaisLattice.__init__(self, lattice_vectors, cells, function, base)
