# This module provides classes that represent VRML objects for use
# in data visualization applications.
#
# Written by: Konrad Hinsen <khinsen@cea.fr>
# With contributions from Frank Horowitz
#                     and Matteo Bertini
# Last revision: 2006-1-31
#

"""This module provides definitions of simple 3D graphics objects and
VRML scenes containing them. The objects are appropriate for data
visualization, not for virtual reality modelling. Scenes can be written
to VRML files or visualized immediately using a VRML browser, whose
name is taken from the environment variable VRML2VIEWER (under Unix).

There are a few attributes that are common to all graphics objects:

  material -- a Material object defining color and surface properties

  comment -- a comment string that will be written to the VRML file

  reuse -- a boolean flag (defaulting to false). If set to one,
           the object may share its VRML definition with other
           objects. This reduces the size of the VRML file, but
           can yield surprising side effects in some cases.


This module uses the VRML 2.0 definition, also known as VRML97. For
the original VRML 1, use the module VRML, which uses exactly the same
interface. There is another almost perfectly compatible module VMD,
which produces input files for the molecular visualization program
VMD.

Example:

>>> from Scientific.Visualization.VRML2 import *
>>> scene = Scene([])
>>> scale = ColorScale(10.)
>>> for x in range(11):
>>>     color = scale(x)
>>>     scene.addObject(Cube(Vector(x, 0., 0.), 0.2,
>>>                          material=Material(diffuse_color = color)))
>>> scene.view()
"""


from Scientific.IO.TextFile import TextFile
from Scientific.Geometry import Transformation, Vector, ex, ey, ez, nullVector
from Scientific import N
import os, string, tempfile

from Color import *

#
# VRML file
#
class SceneFile:

    def __init__(self, filename, mode = 'r'):
        if mode == 'r':
            raise TypeError, 'Not implemented.'
        self.file = TextFile(filename, 'w')
        self.file.write('#VRML V2.0 utf8\n')
        self.file.write('Transform { children [\n')
        self.memo = {}
        self.name_counter = 0

    def __del__(self):
        self.close()

    def writeString(self, data):
        self.file.write(data)

    def close(self):
        if self.file is not None:
            self.file.write(']}\n')
            self.file.close()
            self.file = None

    def write(self, object):
        object.writeToFile(self)

    def uniqueName(self):
        self.name_counter = self.name_counter + 1
        return 'i' + `self.name_counter`

VRMLFile = SceneFile

#
# Scene
#
class Scene:

    """VRML scene

    A VRML scene is a collection of graphics objects that can be
    written to a VRML file or fed directly to a VRML browser.

    Constructor: Scene(|objects|=None, |cameras|=None, **|options|)

    Arguments:

    |objects| -- a list of graphics objects or 'None' for an empty scene

    |cameras| -- a list of cameras

    |options| -- options as keyword arguments (none defined at the moment;
                 this argument is provided for compatibility with
                 other modules)
    """

    def __init__(self, objects = None, cameras = None, **options):
        if objects is None:
            self.objects = []
        elif type(objects) == type([]):
            self.objects = objects
        else:
            self.objects = [objects]
        if cameras is None:
            self.cameras = []
        else:
            self.cameras = cameras

    def __len__(self):
        return len(self.objects)

    def __getitem__(self, item):
        return self.object[item]

    def addObject(self, object):
        "Adds |object| to the list of graphics objects."
        self.objects.append(object)

    def addCamera(self, camera):
        "Adds |camera| to the list of cameras."
        self.cameras.append(camera)

    def writeToFile(self, filename):
        "Writes the scene to a VRML file with name |filename|."
        file = VRMLFile(filename, 'w')
        if self.cameras:
            for camera in self.cameras:
                camera.writeToFile(file)
        for o in self.objects:
            o.writeToFile(file)
        file.close()

    def view(self, *args):
        "Start a VRML browser for the scene."
        import sys
        filename = tempfile.mktemp()+'.wrl'
        if sys.platform == 'win32':
            import win32api
            self.writeToFile(filename)
            win32api.ShellExecute(0, "open", filename, None, "", 1)
        elif os.environ.has_key('VRML2VIEWER'):
            self.writeToFile(filename)
            if os.fork() == 0:
                os.system(os.environ['VRML2VIEWER'] + ' ' + filename +
                          ' 1> /dev/null 2>&1')
                os.unlink(filename)
                os._exit(0)
        else:
            print 'No VRML2 viewer defined'

#
# Camera class
#
class Camera:

    """Camera/viewpoint for a scene

    Constructor: Camera(|position|, |orientation|, |description|,
                        |field_of_view|)

    Arguments:

    |position| -- the location of the camera (a vector)

    |orientation| -- an (axis, angle) tuple in which the axis is
                     a vector and angle a number (in radians);
                     axis and angle specify a rotation with respect
                     to the standard orientation along the negative z axis

    |description| -- a label for the viewpoint (a string)

    |field_of_view| -- the field of view (a positive number)
    """

    def __init__(self, position=None, orientation=None,
                 description=None, field_of_view=None):
        self.field_of_view = field_of_view
        self.orientation = orientation
        self.position = position
        self.description = description

    def writeToFile(self, file):
        file.writeString('Viewpoint {\n')
        if self.field_of_view != None:
            file.writeString('fieldOfView %f\n' % self.field_of_view)
        if self.orientation != None:
            axis, angle = self.orientation
            axis = axis.normal()
            file.writeString('orientation %f %f %f %f\n' % \
                             (axis[0], axis[1], axis[2], angle))
        if self.position != None:
            file.writeString('position %f %f %f\n' % \
                             (self.position[0], \
                              self.position[1], \
                              self.position[2]))
        if self.description != None:
            file.writeString('description "%s"' % \
                             self.description)
        file.writeString('}\n')

#
# Navigation Info
#
class NavigationInfo:

    """Navigation Information

    Constructor: NavigationInfo(|speed|, |type|)

    Arguments:

    |speed| -- walking speed in length units per second

    |type| --  one of 'WALK', 'EXAMINE', 'FLY', 'NONE', 'ANY'
    """

    def __init__(self, speed=100.0, type="EXAMINE"):
        self.speed = speed
        self.type = type

    def writeToFile(self, file):
        file.writeString('NavigationInfo {\n')
        file.writeString('speed %f\n' % self.speed )
        file.writeString('type [ ')
        if self.type != "ANY":
            file.writeString('"%s", ' % self.type)
        file.writeString('"ANY" ]\n')
        file.writeString('}\n')

#
# Base class for everything that produces nodes
#
class VRMLObject:

    def __init__(self, attr):
        self.attr = {}
        for key, value in attr.items():
            if key in self.attribute_names:
                self.attr[key] = value
            else:
                raise AttributeError, 'illegal attribute: ' + str(key)

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
        raise AttributeError, 'Class ' + self.__class__.__name__ + \
              ' does not implement file output.'

#
# Shapes
#
class ShapeObject(VRMLObject):

    def __init__(self, attr, rotation, translation, reference_point):
        VRMLObject.__init__(self, attr)
        if rotation is None:
            rotation = Transformation.Rotation(ez, 0.)
        else:
            rotation = apply(Transformation.Rotation, rotation)
        if translation is None:
            translation = Transformation.Translation(Vector(0.,0.,0.))
        else:
            translation = Transformation.Translation(translation)
        self.transformation = translation*rotation
        self.reference_point = reference_point

    attribute_names = VRMLObject.attribute_names + ['material', 'reuse']

    def __add__(self, other):
        return Group([self]) + Group([other])

    def writeToFile(self, file):
        comment = self['comment']
        if comment is not None:
            file.writeString('# ' + comment + '\n')
        file.writeString('Transform{\n')
        vector = self.transformation.translation().displacement()
        axis, angle = self.transformation.rotation().axisAndAngle()
        trans_flag = vector.length() > 1.e-4
        rot_flag = abs(angle) > 1.e-4
        if trans_flag:
            file.writeString('translation %f %f %f\n' %
                                (vector[0], vector[1], vector[2]))
        if rot_flag:
            file.writeString('rotation %f %f %f %f\n' %
                                (axis[0], axis[1], axis[2], angle))
        material = self['material']
        reuse = self['reuse']
        file.writeString('children [\n')
        if reuse:
            key = self.memoKey() + (material, self.__class__)
            if file.memo.has_key(key):
                file.writeString('USE ' + file.memo[key] + '\n')
                self.use(file)
                if material is not None:
                    material.use(file)
            else:
                name = file.uniqueName()
                file.memo[key] = name
                file.writeString('DEF ' + name + ' Shape{\n')
                if material is not None:
                    file.writeString('appearance ')
                    material.writeToFile(file)
                file.writeString('geometry ')
                self.writeSpecification(file)
                file.writeString('}\n')
        else:
            file.writeString('Shape{')
            if material is not None:
                file.writeString('appearance ')
                material.writeToFile(file)
            file.writeString('geometry ')
            self.writeSpecification(file)
            file.writeString('}\n')
        file.writeString(']}\n')

    def use(self, file):
        pass

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
        ShapeObject.__init__(self, attr, None, center, center)

    def writeSpecification(self, file):
        file.writeString('Sphere{radius ' + `self.radius` + '}\n')

    def memoKey(self):
        return (self.radius, )

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
        ShapeObject.__init__(self, attr, None, center, center)

    def writeSpecification(self, file):
        file.writeString('Box{size' + 3*(' ' + `self.edge`) + '}\n')

    def memoKey(self):
        return (self.edge, )

class LinearOrientedObject(ShapeObject):

    def __init__(self, attr, point1, point2):
        center = 0.5*(point1+point2)
        axis = point2-point1
        self.height = axis.length()
        if self.height > 0:
            axis = axis/self.height
            rot_axis = ey.cross(axis)
            sine = rot_axis.length()
            cosine = ey*axis
            angle = Transformation.angleFromSineAndCosine(sine, cosine)
            if abs(angle) < 1.e-4 or abs(angle-2.*N.pi) < 1.e-4:
                rotation = None
            else:
                if abs(sine) < 1.e-4:
                    rot_axis = ex
                rotation = (rot_axis, angle)
        else:
            rotation = None
        ShapeObject.__init__(self, attr, rotation, center, center)

class Cylinder(LinearOrientedObject):

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
        LinearOrientedObject.__init__(self, attr, point1, point2)

    def writeSpecification(self, file):
        file.writeString('Cylinder{')
        if not self.faces[0]:
            file.writeString('side FALSE ')
        if not self.faces[1]:
            file.writeString('bottom FALSE ')
        if not self.faces[2]:
            file.writeString('top FALSE ')
        file.writeString('radius ' + `self.radius` + \
                         ' height ' + `self.height` + '}\n')

    def memoKey(self):
        return (self.radius, self.height, self.faces)


class Cone(LinearOrientedObject):

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
        LinearOrientedObject.__init__(self, attr, point2, point1)

    def writeSpecification(self, file):
        file.writeString('Cone{')
        if not self.face:
            file.writeString('bottom FALSE ')
        file.writeString('bottomRadius ' + `self.radius` + \
                         ' height ' + `self.height` + '}\n')

    def memoKey(self):
        return (self.radius, self.height, self.face)

class Line(ShapeObject):

    """Line

    Constructor: Line(|point1|, |point2|, **|attributes|)

    Arguments:

    |point1|, |point2| -- the end points of the line (vectors)

    |attributes| -- any graphics object attribute
    """

    def __init__(self, point1, point2, **attr):
        self.points = (point1, point2)
        center = 0.5*(point1+point2)
        ShapeObject.__init__(self, attr, None, None, center)

    def writeSpecification(self, file):
        p0 = "%f %f %f" % self.points[0]
        p1 = "%f %f %f" % self.points[1]
        file.writeString('IndexedLineSet{coord Coordinate{point ')
        file.writeString('[%s,\n%s]} coordIndex[0,1,-1]}\n' % (p0, p1))

    def memoKey(self):
        return tuple(self.points[0]) + tuple(self.points[1])

class PolyLines(ShapeObject):

    """Multiple connected lines

    Constructor: PolyLines(|points|, **|attributes|)

    Arguments:

    |points| -- a sequence of points to be connected by lines

    |attributes| -- any graphics object attribute
    """

    def __init__(self, points, **attr):
        self.points = points
        ShapeObject.__init__(self, attr, None, None, Vector(0., 0., 0.))

    def writeSpecification(self, file):
        s = ['IndexedLineSet{coord Coordinate{point [',]
        for p in self.points:
            s.append('%f %f %f,' % (p[0], p[1], p[2]))
        s[-1] = s[-1][:-1] + ']} coordIndex'
        file.writeString("\n".join(s))
        file.writeString(`range(len(self.points))+[-1]` + '}\n')

    def memoKey(self):
        return tuple(map(tuple, self.points))


class Polygons(ShapeObject):

    """Polygons

    Constructor: Polygons(|points|, |index_lists|, **|attributes|)

    Arguments:

    |points| -- a sequence of points

    |index_lists| -- a sequence of index lists, one for each polygon.
                     The index list for a polygon defines which points
                     in |points| are vertices of the polygon.

    |attributes| -- any graphics object attribute
    """

    def __init__(self, points, index_lists, **attr):
        self.points = points
        self.index_lists = index_lists
        ShapeObject.__init__(self, attr, None, None, Vector(0.,0.,0.))

    def writeSpecification(self, file):
        s = ['IndexedFaceSet{coord Coordinate{point [',]
        for v in self.points[:-1]:
            s.append('%f %f %f,' % (v[0], v[1], v[2]))
        v = self.points[-1]
        s.append('%f %f %f\n]} coordIndex[' % (v[0], v[1], v[2]))
        for polygon in self.index_lists:
            s.append(",".join(map(str, polygon) + ["-1,"]))
        s.append(']}\n')
        file.writeString("\n".join(s))

    def memoKey(self):
        return (tuple(map(tuple, self.points)),
                tuple(map(tuple, self.index_lists)))

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

    def writeToFile(self, file):
        for o in self.objects:
            o.writeToFile(file)

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
class Material(VRMLObject):

    """Material for graphics objects

    A material defines the color and surface properties of an object.

    Constructor: Material(**|attributes|)

    The attributes are "ambient_color", "diffuse_color", "specular_color",
    "emissive_color", "shininess", and "transparency".
    """

    def __init__(self, **attr):
        VRMLObject.__init__(self, attr)

    attribute_names = VRMLObject.attribute_names + \
                      ['ambient_color', 'diffuse_color', 'specular_color',
                       'emissive_color', 'shininess', 'transparency']

    attribute_conversion = {'ambient_color': 'ambientColor',
                            'diffuse_color': 'diffuseColor',
                            'specular_color': 'specularColor',
                            'emissive_color': 'emissiveColor',
                            'shininess': 'shininess',
                            'transparency': 'transparency'}

    def writeToFile(self, file):
        if file.memo.has_key(self):
            file.writeString('USE ' + file.memo[self] + '\n')
        else:
            name = file.uniqueName()
            file.memo[self] = name
            file.writeString('DEF '+name+' Appearance{material Material{\n')
            for key, value in self.attr.items():
                file.writeString(self.attribute_conversion[key] + ' ' + \
                                 str(value) + '\n')
            file.writeString('}}\n')

    def use(self, file):
        pass

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

def EmissiveMaterial(color):
    "Returns a material with the 'emissive color' attribute set to |color|."
    if type(color) is type(''):
        color = ColorByName(color)
    try:
        return emissive_material_dict[color]
    except KeyError:
        m = Material(emissive_color = color)
        emissive_material_dict[color] = m
        return m

emissive_material_dict = {}

#
# Test code
#
if __name__ == '__main__':

    if 1:
        spheres = DiffuseMaterial('green')
        links = DiffuseMaterial('red')
        s1 = Sphere(nullVector, 0.05, material = spheres, reuse = 1)
        s2 = Sphere(ex, 0.05, material = spheres, reuse = 1)
        s3 = Sphere(ey, 0.05, material = spheres, reuse = 1)
        s4 = Sphere(ez, 0.05, material = spheres, reuse = 1)
        a1 = Arrow(nullVector, ex, 0.01, material = links)
        a2 = Arrow(nullVector, ey, 0.01, material = links)
        a3 = Arrow(nullVector, ez, 0.01, material = links)
        scene = Scene([a1, a2, a3, s1, s2, s3, s4])
        scene.view()

    if 0:
        scene = Scene([])
        scale = ColorScale(10.)
        for x in range(11):
            color = scale(x)
            m = Material(diffuse_color = color)
            scene.addObject(Cube(Vector(x,0.,0.), 0.2, material=m))
        scene.view()

    if 0:
        points = [Vector(0., 0., 0.),
                  Vector(0., 1., 0.),
                  Vector(1., 1., 0.),
                  Vector(1., 0., 0.),
                  Vector(1., 0., 1.),
                  Vector(1., 1., 1.)]
        indices = [[0, 1, 2, 3, 0], [3, 4, 5, 2, 3]]
        scene = Scene(Polygons(points, indices,
                               material=DiffuseMaterial('yellow')))
        scene.view()

    if 0:
        points = [Vector(0., 0., 0.),
                  Vector(0., 1., 0.),
                  Vector(1., 1., 0.),
                  Vector(1., 0., 0.),
                  Vector(1., 0., 1.),
                  Vector(1., 1., 1.)]
        scene = Scene(PolyLines(points, material = EmissiveMaterial('yellow')))
        scene.view()
