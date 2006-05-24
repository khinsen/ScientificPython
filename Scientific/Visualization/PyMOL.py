# This module provides classes that represent graphics objects to be
# output to PyMOL. This module is as compatible as possible with module
# VRML. Important differences:
# - No general polygon objects (yet)
# - Only the 'diffuse color' attribute of materials is used for rendering.
#
# Written by: Konrad Hinsen <khinsen@cea.fr>
# Last revision: 2005-9-5
#

"""This module provides definitions of simple 3D graphics objects and
scenes containing them, in a form that can be fed to the molecular
visualization program PyMOL. Scripts that use this module, directly
or indirectly, must be run from inside PyMOL, otherwise they will
terminate with an error message

There are a few attributes that are common to all graphics objects:

  material -- a Material object defining color and surface properties

  comment -- a comment string that will be written to the VRML file

  reuse -- a boolean flag (defaulting to false). If set to one,
           the object may share its VRML definition with other
           objects. This reduces the size of the VRML file, but
           can yield surprising side effects in some cases.

This module is almost compatible with the modules VRML and VRML2, which
provide visualization by VRML browsers. There are no Polygon objects,
and the only material attribute supported is diffuse_color.

Example:

>>>from Scientific.Visualization.PyMOL import *    
>>>scene = Scene([])
>>>scale = ColorScale(10.)
>>>for x in range(11):
>>>    color = scale(x)
>>>    scene.addObject(Cube(Vector(x, 0., 0.), 0.2,
>>>                         material=Material(diffuse_color = color)))
>>>scene.view()
"""

import sys
if not sys.modules.has_key('pymol'):
    raise SystemExit("You have to run this script from inside PyMOL!")
del sys

from Scientific.IO.TextFile import TextFile
from Scientific.Geometry import Transformation, Vector, VectorModule
import os, string, sys, tempfile

from Color import *

from pymol import cmd, cgo

#
# Scene
#
class Scene:

    """PyMOL scene

    A PyMOL scene is a collection of graphics objects that can be
    loaded into PyMOL.

    Constructor: Scene(|objects|=None, **|options|)

    Arguments:

    |objects| -- a list of graphics objects or 'None' for an empty scene

    |options| -- options as keyword arguments. This is provided for
                 compatibility only, no options have any effect for
                 PyMOL graphics
    """

    def __init__(self, objects=None, **options):
        if objects is None:
            self.objects = []
        elif type(objects) == type([]):
            self.objects = objects
        else:
            self.objects = [objects]

    def __len__(self):
        return len(self.objects)

    def __getitem__(self, item):
        return self.object[item]

    def addObject(self, object):
        "Adds |object| to the list of graphics objects."
        self.objects.append(object)

    def writeToFile(self, filename, delete = 0):
        raise ValueError("no file support for PyMOL graphics")

    def view(self, name="external graphics"):
        "Load the scene into PyMOL"
        pymol_objects = []
        for o in self.objects:
            pymol_objects.extend(o.getPymolObjects())
        cmd.load_cgo(pymol_objects, name)

#
# Base class for everything that produces graphic objects
#
class PyMOLObject:

    def __init__(self, attr):
        self.attr = {}
        for key, value in attr.items():
            if key in self.attribute_names:
                self.attr[key] = value
            else:
                raise AttributeError('illegal attribute: ' + str(key))

    attribute_names = ['comment']

    def __getitem__(self, attr):
        try:
            return self.attr[attr]
        except KeyError:
            return None

    def __setitem__(self, attr, value):
        self.attr[attr] = value

    def __copy__(self):
        return copy.deepcopy(self)

    def writeToFile(self, file):
        raise AttributeError('Class ' + self.__class__.__name__ +
                              ' does not implement file output.')

    def getPymolObjects(self):
        "Return a list of pymol.cgo objects"
        raise AttributeError("to be implemented in subclasses")

#
# Molecules (via PDB)
#
class Molecules(PyMOLObject):

    """Molecules from a PDB file

    Constructor: Molecules(|pdb_file|)
    """
    
    def __init__(self, object, **attr):
        PyMOLObject.__init__(self, attr)
        self.object = object

    def getPymolObjects(self):
        cmd.load_pdb(self.object)
        return []

#
# Shapes
#
class ShapeObject(PyMOLObject):

    def __init__(self, attr):
        PyMOLObject.__init__(self, attr)

    attribute_names = PyMOLObject.attribute_names + ['material']

    def __add__(self, other):
        return Group([self]) + Group([other])

    def use(self, file):
        pass

    def getPymolObjects(self):
        material = self['material']
        if material is None:
            material = DiffuseMaterial('white')
        return self.cgoObjects(material)

class Sphere(ShapeObject):

    """Sphere

    Constructor: Sphere(|center|, |radius|, **|attributes|)

    Arguments:

    |center| -- the center of the sphere (a vector)

    |radius| -- the sphere radius (a positive number)

    |attributes| -- any graphics object attribute
    """
    
    def __init__(self, center, radius, **attr):
        self.radius = radius
        self.center = center
        ShapeObject.__init__(self, attr)

    def cgoObjects(self, material):
        rgb = material.getRGB()
        return [cgo.COLOR] + rgb \
                + [cgo.SPHERE] + list(10.*self.center) + [10.*self.radius]


class Cube(ShapeObject):

    """Cube

    Constructor: Cube(|center|, |edge|, **|attributes|)

    Arguments:

    |center| -- the center of the cube (a vector)

    |edge| -- the length of an edge  (a positive number)

    |attributes| -- any graphics object attribute

    The edges of a cube are always parallel to the coordinate axes.
    """
    
    def __init__(self, center, edge, **attr):
        self.edge = edge
        self.center = center
        ShapeObject.__init__(self, attr)

    def cgoObjects(self, material):
        raise ValueError("cubes not implemented yet")


class Cylinder(ShapeObject):

    """Cylinder

    Constructor: Cylinder(|point1|, |point2|, |radius|,
                          |faces|='(1, 1, 1)', **|attributes|)

    Arguments:

    |point1|, |point2| -- the end points of the cylinder axis (vectors)

    |radius| -- the radius  (a positive number)

    |attributes| -- any graphics object attribute

    |faces| -- a sequence of three boolean flags, corresponding to
               the cylinder hull and the two circular end pieces,
               specifying for each of these parts whether it is visible
               or not.
    """
    
    def __init__(self, point1, point2, radius, faces = (1, 1, 1), **attr):
        self.faces = faces
        self.radius = radius
        self.point1 = point1
        self.point2 = point2
        ShapeObject.__init__(self, attr)

    def cgoObjects(self, material):
        rgb = material.getRGB()
        return [cgo.CYLINDER] \
               + list(10.*self.point1) \
               + list(10.*self.point2) \
               + [10.*self.radius] \
               + 2*rgb


class Cone(ShapeObject):

    """Cone

    Constructor: Cone(|point1|, |point2|, |radius|, |face|='1', **|attributes|)

    Arguments:

    |point1|, |point2| -- the end points of the cylinder axis (vectors).
                          |point1| is the tip of the cone.

    |radius| -- the radius  (a positive number)

    |attributes| -- any graphics object attribute

    |face| -- a boolean flag, specifying if the circular bottom is visible
    """

    def __init__(self, point1, point2, radius, face = 1, **attr):
        self.face = face
        self.radius = radius
        self.point1 = point1
        self.point2 = point2
        ShapeObject.__init__(self, attr)

    def cgoObjects(self, material):
        raise ValueError("cones not implemented yet")


class Line(ShapeObject):

    """Line

    Constructor: Line(|point1|, |point2|, **|attributes|)

    Arguments:

    |point1|, |point2| -- the end points of the line (vectors)

    |attributes| -- any graphics object attribute
    """
    
    def __init__(self, point1, point2, **attr):
        self.point1 = point1
        self.point2 = point2
        ShapeObject.__init__(self, attr)

    def cgoObjects(self, material):
        rgb = material.getRGB()
        return [cgo.COLOR] + rgb \
                + [cgo.BEGIN, cgo.LINES,
                   cgo.VERTEX, self.point1[0], self.point1[1], self.point1[2],
                   cgo.VERTEX, self.point2[0], self.point2[1], self.point2[2],
                   cgo.END]

#
# Groups
#
class Group:

    def __init__(self, objects, **attr):
        self.objects = []
        for o in objects:
            if isGroup(o):
                self.objects = self.objects + o.objects
            else:
                self.objects.append(o)
        for key, value in attr.items():
            for o in self.objects:
                o[key] = value

    is_group = 1

    def __len__(self):
        return len(self.objects)

    def __getitem__(self, item):
        return self.object[item]

    def __coerce__(self, other):
        if not isGroup(other):
            other = Group([other])
        return (self, other)

    def __add__(self, other):
        return Group(self.objects + other.objects)

    def getPymolObjects(self):
        objects = []
        for o in self.objects:
            objects.extend(o.getPymolObjects())
        return objects

def isGroup(x):
    return hasattr(x, 'is_group')

#
# Composite Objects
#
class Arrow(Group):

    """Arrow

    An arrow consists of a cylinder and a cone.

    Constructor: Arrow(|point1|, |point2|, |radius|, **|attributes|)

    Arguments:

    |point1|, |point2| -- the end points of the arrow (vectors).
                          |point2| defines the tip of the arrow.

    |radius| -- the radius of the arrow shaft (a positive number)

    |attributes| -- any graphics object attribute
    """

    def __init__(self, point1, point2, radius, **attr):
        axis = point2-point1
        height = axis.length()
        axis = axis/height
        cone_height = min(height, 4.*radius)
        cylinder_height = height - cone_height
        junction = point2-axis*cone_height
        cone = apply(Cone, (point2, junction, 0.75*cone_height), attr)
        objects = [cone]
        if cylinder_height > 0.005*radius:
            cylinder = apply(Cylinder, (point1, junction, radius), attr)
            objects.append(cylinder)
        Group.__init__(self, objects)

#
# Materials
#
class Material(PyMOLObject):

    """Material for graphics objects

    A material defines the color and surface properties of an object.

    Constructor: Material(**|attributes|)

    The accepted attributes are "ambient_color", "diffuse_color",
    "specular_color", "emissive_color", "shininess", and "transparency".
    Only "diffuse_color" is used, the others are permitted for compatibility
    with the VRML modules.
    """

    def __init__(self, **attr):
        PyMOLObject.__init__(self, attr)

    attribute_names = PyMOLObject.attribute_names + \
                      ['ambient_color', 'diffuse_color', 'specular_color',
                       'emissive_color', 'shininess', 'transparency']

    def getRGB(self): 
        try:
            color = self.attr['diffuse_color']
        except KeyError:
            color = Color((1., 1., 1.))
        return [color.rgb[0], color.rgb[1], color.rgb[2]]

#
# Predefined materials
#
def DiffuseMaterial(color):
    "Returns a material with the 'diffuse color' attribute set to |color|."
    if type(color) is type(''):
        color = ColorByName(color)
    try:
        return diffuse_material_dict[color]
    except KeyError:
        m = Material(diffuse_color = color)
        diffuse_material_dict[color] = m
        return m

diffuse_material_dict = {}

EmissiveMaterial = DiffuseMaterial

#
# Test code
#
if __name__ == '__main__':

    if 0:
        spheres = DiffuseMaterial('green')
        links = DiffuseMaterial('red')
        s1 = Sphere(VectorModule.null, 0.05, material = spheres)
        s2 = Sphere(VectorModule.ex, 0.05, material = spheres)
        s3 = Sphere(VectorModule.ey, 0.05, material = spheres)
        s4 = Sphere(VectorModule.ez, 0.05, material = spheres)
        a1 = Arrow(VectorModule.null, VectorModule.ex, 0.01, material = links)
        a2 = Arrow(VectorModule.null, VectorModule.ey, 0.01, material = links)
        a3 = Arrow(VectorModule.null, VectorModule.ez, 0.01, material = links)
        scene = Scene([s1, s2, s3, s4, a1, a2, a3])
        scene.view()

    if 0:
        scene = Scene([])
        scale = SymmetricColorScale(10., 10)
        for x in range(-10, 11):
            color = scale(x)
            m = Material(diffuse_color = color)
            scene.addObject(Cube(Vector(x,0.,0.), 0.2, material=m))
        scene.view()

    if 1:
        scene = Scene([])
        scale = ColorScale(10.)
        for x in range(11):
            color = scale(x)
            m = Material(diffuse_color = color)
            scene.addObject(Cube(Vector(x,0.,0.), 0.2, material=m))
        scene.view()

