# This module provides classes that represent graphics objects to be
# output to Chimera. This module is as compatible as possible with module
# VRML. Important differences:
# - No general polygon objects.
# - Only the 'diffuse color' attribute of materials is used for rendering.
#
# Written by: Konrad Hinsen <hinsen@cnrs-orleans.fr>
# Last revision: 2010-1-11
#

"""
Definitions of simple 3D graphics objects and scenes containing them,
in a form that can be fed to the molecular visualization program Chimera

Scenes can either be written as Chimea BILD files, or visualized directly
when the code is run from inside Chimera

This module is almost compatible with the modules VRML and VRML2, which
provide visualization by VRML browsers. There is no Polygon class,
and the only material attribute supported is diffuse_color.

Example::

  >>> from Scientific.Visualization.Chimera import *    
  >>> scene = Scene([])
  >>> scale = ColorScale(10.)
  >>> for x in range(11):
  >>>     color = scale(x)
  >>>     scene.addObject(Cube(Vector(x, 0., 0.), 0.2,
  >>>                          material=Material(diffuse_color = color)))
  >>> scene.view()
"""


from Scientific.IO.TextFile import TextFile
from Scientific.Geometry import Transformation, Vector, ex, ey, ez
from cStringIO import StringIO
import os, sys

from Scientific.Visualization.Color import *

#
# BILD file
#
class SceneFile(object):

    def __init__(self, filename, mode = 'r', scale = 1.):
        if mode == 'r':
            raise TypeError('Not yet implemented.')
        self.file = TextFile(filename, 'w')
        self.filename = filename
        self._init(scale)
        
    def _init(self, scale):
        self.memo = {}
        self.scale = scale

    def __del__(self):
        self.close()
    
    def writeString(self, data):
        self.file.write(data)

    def writeVector(self, v):
        self.writeString(" %g %g %g " % tuple(v))

    def close(self):
        self.file.close()

    def write(self, object):
        object.writeToFile(self)

class InternalSceneFile(SceneFile):

    def __init__(self, scale=1.):
        self.file = StringIO()
        self._init(scale)

    def close(self):
        return

    def __str__(self):
        return self.file.getvalue()

#
# Scene
#
class Scene(object):

    """
    Chimera scene

    A Chimera scene is a collection of graphics objects that can be
    loaded into Chimera
    """

    def __init__(self, objects=None, **options):
        """
        @param objects: a list of graphics objects, or C{None} for
                        an empty scene
        @type objects: C{list} or C{NoneType}
        @param options: options as keyword arguments
        @keyword scale: a scale factor applied to all coordinates of
                        geometrical objects B{except} for molecule objects,
                        which cannot be scaled
        @type scale: positive number
        """
        if objects is None:
            self.objects = []
        elif type(objects) == type([]):
            self.objects = objects
        else:
            self.objects = [objects]
        try:
            self.scale = options['scale']
        except KeyError:
            self.scale = 1.
        try:
            self.name = options['name']
        except KeyError:
            self.name = 'ScientificPython graphics'

    def __len__(self):
        """
        @returns: the number of graphics objects in the scene
        @rtype: C{int}
        """
        return len(self.objects)

    def __getitem__(self, item):
        """
        @param item: an index
        @type item: C{int}
        @returns: the graphics object at the index position
        @rtype: L{ChimeraObject}
        """
        return self.object[item]

    def addObject(self, object):
        """
        @param object: a graphics object to be added to the scene
        @type object: L{ChimeraObject}
        """
        self.objects.append(object)

    def writeToFile(self, filename):
        """
        Write the scene to a Cimera script file

        @param filename: the name of the script
        @type filename: C{str}
        """
        file = SceneFile(filename, 'w', self.scale)
        for o in self.objects:
            o.writeToFile(file)
        file.close()

    def view(self, *args):
        """
        Load the scene into Chimera

        @param args: not used, for compatibility with VRML modules only
        @returns: the Chimera VRML model that was created.
        """
        f = InternalSceneFile(self.scale)
        for o in self.objects:
            o.writeToFile(f)
        f.close()
        import chimera
        return chimera.openModels.open(StringIO(str(f)), type="Bild",
                                       identifyAs=self.name)[0]

    def __str__(self):
        f = InternalSceneFile(self.scale)
        for o in self.objects:
            o.writeToFile(f)
        f.close()
        return str(f)

#
# Base class for everything that produces graphic objects
#
class ChimeraObject:

    """
    Graphics object for Chimera

    This is an abstract base class. Use one of the subclasses to generate
    graphics.
    """

    def __init__(self, attr):
        """
        @param attr: graphics attributes specified by keywords
        @keyword material: color and surface properties
        @type material: L{Material}
        @keyword comment: a comment that is written to the script file
        @type comment: C{str}
        """
        self.attr = {}
        for key, value in attr.items():
            if key in self.attribute_names:
                self.attr[key] = value
            else:
                raise AttributeError('illegal attribute: ' + str(key))

    attribute_names = ['comment']

    def __getitem__(self, attr):
        """
        @param attr: the name of a graphics attribute
        @type attr: C{str}
        @returns: the value of the attribute, or C{None} if the attribute
                  is undefined
        """
        try:
            return self.attr[attr]
        except KeyError:
            return None

    def __setitem__(self, attr, value):
        """
        @param attr: the name of a graphics attribute
        @type attr: C{str}
        @param value: a new value for the attribute
        """
        self.attr[attr] = value

    def __copy__(self):
        return copy.deepcopy(self)

    def writeToFile(self, file):
        raise AttributeError('Class ' + self.__class__.__name__ +
                              ' does not implement file output.')

#
# Shapes
#
class ShapeObject(ChimeraObject):

    """
    Graphics objects representing geometrical shapes

    This is an abstract base class. Use one of the subclasses to generate
    graphics.
    """

    def __init__(self, attr):
        ChimeraObject.__init__(self, attr)

    attribute_names = ChimeraObject.attribute_names + ['material']

    def __add__(self, other):
        return Group([self]) + Group([other])

    def writeToFile(self, file):
        comment = self['comment']
        if comment is not None:
            file.writeString('.comment ' + comment + '\n')
        material = self['material']
        if material is not None:
            material.writeToFile(file)
        self.writeSpecification(file)

    def use(self, file):
        pass


class Sphere(ShapeObject):

    """
    Sphere
    """
    
    def __init__(self, center, radius, **attr):
        """
        @param center: the center of the sphere
        @type center: L{Scientific.Geometry.Vector}
        @param radius: the sphere radius
        @type radius: positive number
        @param attr: graphics attributes as keyword parameters
        """
        self.radius = radius
        self.center = center
        ShapeObject.__init__(self, attr)

    def writeSpecification(self, file):
        file.writeString('.sphere')
        file.writeVector(self.center*file.scale)
        file.writeString(' ' + `self.radius*file.scale` + '\n')


class Cube(ShapeObject):

    """
    Cube

    The edges of a cube are always parallel to the coordinate axes.
    """
    
    def __init__(self, center, edge, **attr):
        """
        @param center: the center of the cube
        @type center: L{Scientific.Geometry.Vector}
        @param edge: the length of an edge
        @type edge: positive number
        @param attr: graphics attributes as keyword parameters
        """
        self.edge = edge
        self.center = center
        ShapeObject.__init__(self, attr)

    def writeSpecification(self, file):
        d = 0.5*self.edge
        semi_diag = Vector(d, d, d)
        file.writeString('.box')
        file.writeVector((self.center-semi_diag)*file.scale)
        file.writeVector((self.center+semi_diag)*file.scale)
        file.writeString('\n')


class Cylinder(ShapeObject):

    """
    Cylinder
    """

    def __init__(self, point1, point2, radius, faces = (1, 1, 1), **attr):
        """
        @param point1: first end point of the cylinder axis
        @type point1: L{Scientific.Geometry.Vector}
        @param point2: second end point of the cylinder axis
        @type point2: L{Scientific.Geometry.Vector}
        @param radius: the cylinder radius
        @type radius: positive number
        @param faces: a sequence of three boolean flags, corresponding to
                      the cylinder hull and the two circular end pieces,
                      specifying for each of these parts whether it is visible
                      or not
        @param attr: graphics attributes as keyword parameters
        """
        self.faces = faces
        self.radius = radius
        self.point1 = point1
        self.point2 = point2
        ShapeObject.__init__(self, attr)

    def writeSpecification(self, file):
        file.writeString('.cylinder')
        file.writeVector(self.point1*file.scale)
        file.writeVector(self.point2*file.scale)
        file.writeString(' ' + `self.radius*file.scale`)
        if self.faces[:2] == (0, 0):
            file.writeString(' open')
        file.writeString('\n')


class Cone(ShapeObject):

    """
    Cone
    """

    def __init__(self, point1, point2, radius, face = 1, **attr):
        """
        @param point1: the tip of the cone
        @type point1: L{Scientific.Geometry.Vector}
        @param point2: end point of the cone axis
        @type point2: L{Scientific.Geometry.Vector}
        @param radius: the radius at the base
        @type radius: positive number
        @param face: a boolean flag, specifying if the circular
                      bottom is visible
        @type face: C{bool}
        @param attr: graphics attributes as keyword parameters
        """
        self.face = face
        self.radius = radius
        self.point1 = point1
        self.point2 = point2
        ShapeObject.__init__(self, attr)

    def writeSpecification(self, file):
        file.writeString('.cone')
        file.writeVector(self.point2*file.scale)
        file.writeVector(self.point1*file.scale)
        file.writeString(' ' + `self.radius*file.scale`)
        if not self.face:
            file.writeString(' open')
        file.writeString('\n')


class Line(ShapeObject):
 
    """
    Line
    """
    
    def __init__(self, point1, point2, **attr):
        """
        @param point1: first end point
        @type point1: L{Scientific.Geometry.Vector}
        @param point2: second end point
        @type point2: L{Scientific.Geometry.Vector}
        @param attr: graphics attributes as keyword parameters
        """
        self.point1 = point1
        self.point2 = point2
        ShapeObject.__init__(self, attr)

    def writeSpecification(self, file):
        file.writeString('.move')
        file.writeVector(self.point1*file.scale)
        file.writeString('\n')
        file.writeString('.draw')
        file.writeVector(self.point2*file.scale)
        file.writeString('\n')


#
# Groups
#
class Group:

    """
    Base class for composite objects
    """

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

    def writeToFile(self, file):
        for o in self.objects:
            o.writeToFile(file)

def isGroup(x):
    return hasattr(x, 'is_group')

#
# Composite Objects
#
class Arrow(Group):

    """
    Arrow

    An arrow consists of a cylinder and a cone.
    """

    def __init__(self, point1, point2, radius, **attr):
        """
        @param point1: starting point of the arrow
        @type point1: L{Scientific.Geometry.Vector}
        @param point2: the tip of the arrow
        @type point2: L{Scientific.Geometry.Vector}
        @param radius: the radius of the shaft
        @type radius: positive number
        @param attr: graphics attributes as keyword parameters
        """
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
class Material(ChimeraObject):

    """
    Material specification for graphics objects

    A material defines the color and surface properties of an object.

    For compatibility with the module L{Scientific.Visualization.VRML},
    many material attributes are accepted but not used in any way.
    """

    def __init__(self, **attr):
        """
        @param attr: material attributes as keyword arguments
        @keyword diffuse_color: the color of a diffusely reflecting surface
        @type diffuse_color: L{Color}
        @keyword emissive_color: not used
        @keyword ambient_color: not used
        @keyword specular_color: not used
        @keyword shininess: not used
        @keyword transparency: not used
        """
        ChimeraObject.__init__(self, attr)

    attribute_names = ChimeraObject.attribute_names + \
                      ['ambient_color', 'diffuse_color', 'specular_color',
                       'emissive_color', 'shininess', 'transparency']

    def writeToFile(self, file):
        try:
            last = file.memo['material']
            if last == self: return
        except KeyError: pass
        try:
            color = self.attr['diffuse_color']
        except KeyError:
            color = Color((1., 1., 1.))
        file.writeString('.color ' + str(color) + '\n')
        file.memo['material'] = self

#
# Predefined materials
#
def DiffuseMaterial(color):
    """
    @param color: a color object or a predefined color name
    @type color: L{Color} or C{str}
    @returns: a material with the 'diffuse color' attribute set to color
    @rtype: L{Material}
    """
    if type(color) is type(''):
        color = ColorByName(color)
    try:
        return _diffuse_material_dict[color]
    except KeyError:
        m = Material(diffuse_color = color)
        _diffuse_material_dict[color] = m
        return m

_diffuse_material_dict = {}

EmissiveMaterial = DiffuseMaterial


#
# Test code
#
if __name__ == '__main__':

    if 0:
        from Scientific.Geometry import ex, ey, ez
        spheres = DiffuseMaterial('green')
        links = DiffuseMaterial('red')
        origin = Vector(0., 0., 0.)
        s1 = Sphere(origin, 0.05, material = spheres)
        s2 = Sphere(ex, 0.05, material = spheres)
        s3 = Sphere(ey, 0.05, material = spheres)
        s4 = Sphere(ez, 0.05, material = spheres)
        a1 = Arrow(origin, ex, 0.01, material = links)
        a2 = Arrow(origin, ey, 0.01, material = links)
        a3 = Arrow(origin, ez, 0.01, material = links)
        scene = Scene([s1, s2, s3, s4, a1, a2, a3])
        print str(scene)

    if 0:
        scene = Scene([])
        scale = SymmetricColorScale(10., 10)
        for x in range(-10, 11):
            color = scale(x)
            m = Material(diffuse_color = color)
            scene.addObject(Cube(Vector(x,0.,0.), 0.2, material=m))
        print str(scene)

    if 1:
        scene = Scene([])
        scale = ColorScale(10.)
        for x in range(11):
            color = scale(x)
            m = Material(diffuse_color = color)
            scene.addObject(Cube(Vector(x,0.,0.), 0.2, material=m))
        print str(scene)

