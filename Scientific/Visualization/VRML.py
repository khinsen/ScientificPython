# This module provides classes that represent VRML objects for use
# in data visualization applications.
#
# Written by: Konrad Hinsen <khinsen@cea.fr>
# Last revision: 2005-9-5
#

"""This module provides definitions of simple 3D graphics objects and
VRML scenes containing them. The objects are appropriate for data
visualization, not for virtual reality modelling. Scenes can be written
to VRML files or visualized immediately using a VRML browser, whose
name is taken from the environment variable VRMLVIEWER (under Unix).

There are a few attributes that are common to all graphics objects:

  material -- a Material object defining color and surface properties

  comment -- a comment string that will be written to the VRML file

  reuse -- a boolean flag (defaulting to false). If set to one,
           the object may share its VRML definition with other
           objects. This reduces the size of the VRML file, but
           can yield surprising side effects in some cases.


This module used the original VRML definition, version 1.0. For the
newer VRML 2 or VRML97, use the module VRML2, which uses exactly the
same interface. There is another almost perfectly compatible module
VMD, which produces input files for the molecular visualization program
VMD.

Example:

>>>from Scientific.Visualization.VRML import *    
>>>scene = Scene([])
>>>scale = ColorScale(10.)
>>>for x in range(11):
>>>    color = scale(x)
>>>    scene.addObject(Cube(Vector(x, 0., 0.), 0.2,
>>>                         material=Material(diffuse_color = color)))
>>>scene.view()
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
            raise TypeError('Not yet implemented.')
        self.file = TextFile(filename, 'w')
        self.file.write('#VRML V1.0 ascii\n')
        self.file.write('Separator {\n')
        self.memo = {}
        self.name_counter = 0

    def __del__(self):
        self.close()

    def writeString(self, data):
        self.file.write(data)

    def close(self):
        if self.file is not None:
            self.file.write('}\n')
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

    |cameras| -- a list of cameras (not yet implemented)

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
        "Adds |camers| to the list of cameras."
        self.cameras.append(camera)

    def writeToFile(self, filename):
        "Writes the scene to a VRML file with name |filename|."
        file = VRMLFile(filename, 'w')
        if self.cameras:
            self.cameras[0].writeToFile(file)
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
        elif os.environ.has_key('VRMLVIEWER'):
            self.writeToFile(filename)
            if os.fork() == 0:
                os.system(os.environ['VRMLVIEWER'] + ' ' + filename +
                          ' 1> /dev/null 2>&1')
                os.unlink(filename)
                os._exit(0)
        else:
            print 'No VRML viewer defined'

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
        file.writeString('TransformSeparator {\n')
        vector = self.transformation.translation().displacement()
        axis, angle = self.transformation.rotation().axisAndAngle()
        trans_flag = vector.length() > 1.e-4
        rot_flag = abs(angle) > 1.e-4
        if trans_flag and rot_flag:
            file.writeString('Transform{translation ' + `vector[0]` + ' ' + \
                             `vector[1]` + ' ' + `vector[2]` +  \
                             ' rotation ' + `axis[0]` + ' ' + `axis[1]` +
                             ' ' + `axis[2]` + ' ' + `angle` + '}\n')
        elif trans_flag:
            file.writeString('Translation{translation ' + `vector[0]` + ' ' + \
                             `vector[1]` + ' ' + `vector[2]` +  '}\n')
        elif rot_flag:
            file.writeString('Rotation{rotation ' + `axis[0]` + ' ' + \
                             `axis[1]` + ' ' + `axis[2]` + ' ' + \
                             `angle` + '}\n')
        material = self['material']
        reuse = self['reuse']
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
                file.writeString('DEF ' + name + ' Group{\n')
                if material is not None:
                    material.writeToFile(file)
                self.writeSpecification(file)
                file.writeString('}\n')
        else:
            if material is not None:
                material.writeToFile(file)
            self.writeSpecification(file)
        file.writeString('}\n')

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
        file.writeString('Cube{width ' + `self.edge` + \
                         ' height ' + `self.edge` + \
                         ' depth ' + `self.edge` + '}\n')

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
        file.writeString('Cylinder{parts ')
        if self.faces == (1,1,1):
            file.writeString('ALL')
        else:
            plist=[]
            if self.faces[0]: plist.append('SIDES')
            if self.faces[1]: plist.append('BOTTOM')
            if self.faces[2]: plist.append('TOP')
            if plist: file.writeString( '(' + string.join(plist,'|') + ')' )
        file.writeString(' radius ' + `self.radius` + \
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
        file.writeString('Cone{parts ')
        if self.face:
            file.writeString('ALL')
        else:
            file.writeString('SIDES')
        file.writeString(' bottomRadius ' + `self.radius` + \
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
        file.writeString('Coordinate3{point [' + \
                         `self.points[0][0]` + ' ' + `self.points[0][1]` + \
                         ' ' + `self.points[0][2]` + ',' + \
                         `self.points[1][0]` + ' ' + `self.points[1][1]` + \
                         ' ' + `self.points[1][2]`  + \
                         ']}IndexedLineSet{coordIndex[0,1,-1]}\n')

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
        s = 'Coordinate3{point ['
        for p in self.points:
            s = s + `p[0]` + ' ' + `p[1]` + ' ' + `p[2]` + ','
        file.writeString(s[:-1] + ']}IndexedLineSet{coordIndex')
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
        file.writeString('Coordinate3{point [')
        for v in self.points[:-1]:
            file.writeString(`v[0]` + ' ' + `v[1]` + ' ' + `v[2]` + ',')
        v = self.points[-1]
        file.writeString(`v[0]` + ' ' + `v[1]` + ' ' + `v[2]` + \
                         ']}IndexedFaceSet{coordIndex[')
        for polygon in self.index_lists:
            for index in polygon:
                file.writeString(`index`+',')
            file.writeString('-1,')
        file.writeString(']}\n')

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
        try:
            last = file.memo['material']
            if last == self: return
        except KeyError: pass
        if file.memo.has_key(self):
            file.writeString('USE ' + file.memo[self] + '\n')
        else:
            name = file.uniqueName()
            file.memo[self] = name
            file.writeString('DEF ' + name + ' Material{\n')
            for key, value in self.attr.items():
                file.writeString(self.attribute_conversion[key] + ' ' + \
                                 str(value) + '\n')
            file.writeString('}\n')
        file.memo['material'] = self

    def use(self, file):
        file.memo['material'] = self

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
        spheres = DiffuseMaterial('brown')
        links = DiffuseMaterial('orange')
        s1 = Sphere(nullVector, 0.05, material = spheres, reuse = 1)
        s2 = Sphere(ex, 0.05, material = spheres, reuse = 1)
        s3 = Sphere(ey, 0.05, material = spheres, reuse = 1)
        s4 = Sphere(ez, 0.05, material = spheres, reuse = 1)
        a1 = Arrow(nullVector, ex, 0.01, material = links)
        a2 = Arrow(nullVector, ey, 0.01, material = links)
        a3 = Arrow(nullVector, ez, 0.01, material = links)
        scene = Scene([s1, s2, s3, s4, a1, a2, a3])
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
                               material=DiffuseMaterial('blue')))
        scene.view()

    if 0:
        points = [Vector(0., 0., 0.),
                  Vector(0., 1., 0.),
                  Vector(1., 1., 0.),
                  Vector(1., 0., 0.),
                  Vector(1., 0., 1.),
                  Vector(1., 1., 1.)]
        scene = Scene(PolyLines(points, material = DiffuseMaterial('black')))
        scene.view()
