# VPython interface
#
# Written by: Konrad Hinsen <hinsen@cnrs-orleans.fr>
# Last revision: 2005-9-5
#

from Scientific.Geometry import Transformation, Vector, VectorModule
import os, string, sys, tempfile
if not sys.modules.has_key('pythondoc'):
    import visual

from Color import *

#
# Scene
#
class Scene:

    """VPython scene

    A VPython scene is a collection of graphics objects that can be
    shown in a VPython window. When the "view" method is called,
    a new window is created and the graphics objects are displayed
    in it.

    Constructor: Scene(|objects|=None, **|options|)

    Arguments:

    |objects| -- a list of graphics objects or 'None' for an empty scene

    |options| -- options as keyword arguments: "title" (the window title,
                 default: "VPython scene"),  "width" (the window width,
                 default: 300), "height" (the window height, default: 300),
                 "background" (the background color, default: 'black')
    """

    def __init__(self, objects = None, **options):
        if objects is None:
            self.objects = []
        elif type(objects) == type([]):
            self.objects = objects
        else:
            self.objects = [objects]
        self.options = {"title": "VPython Scene",
                        "width": 300,
                        "height": 300,
                        "background": "black"}
        for key, value in options.items():
            if self.options.has_key(key):
                self.options[key] = value
            else:
                raise ValueError("undefined option: " + repr(key))

    def __len__(self):
        return len(self.objects)

    def __getitem__(self, item):
        return self.object[item]

    def addObject(self, object):
        "Adds |object| to the list of graphics objects."
        self.objects.append(object)

    def view(self):
        "Open a VPython window for the scene."
        color = self.options["background"]
        if type(color) == type(''):
            color = ColorByName(color)
        self.window = visual.display(title = self.options["title"],
                                     width = self.options["width"],
                                     height = self.options["height"],
                                     background = color.rgb,
                                     exit = 0)
        for o in self.objects:
            o.display(self.window)

#
# Base classes for graphics objects
#
class GraphicsObject:

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


class ShapeObject(GraphicsObject):

    attribute_names = ['comment', 'material', 'reuse']

    def __add__(self, other):
        return Group([self]) + Group([other])

    def display(self, window):
        material = self.attr.get('material', None)
        if material is None:
            color = ColorByName('white')
        else:
            color = material.attr.get('emissive_color', None)
            if color is None:
                color = material.attr.get('diffuse_color', None)
            if color is None:
                color = ColorByName('white')
        window.foreground = color.rgb
        self.show(window)

#
# Specific shape objects
#
class Sphere(ShapeObject):

    """Sphere

    Constructor: Sphere(|center|, |radius|, **|attributes|)

    Arguments:

    |center| -- the center of the sphere (a vector)

    |radius| -- the sphere radius (a positive number)

    |attributes| -- any graphics object attribute
    """
    
    def __init__(self, center, radius, **attr):
        self.center = center
        self.radius = radius
        ShapeObject.__init__(self, attr)

    def show(self, window):
        self.object = visual.sphere(pos=tuple(self.center), radius=self.radius)


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
        self.center = center
        self.edge = edge
        ShapeObject.__init__(self, attr)

    def show(self, window):
        self.object = visual.box(pos = tuple(self.center),
                                 length = self.edge,
                                 height = self.edge,
                                 width = self.edge)


class Cylinder(ShapeObject):

    """Cylinder

    Constructor: Cylinder(|point1|, |point2|, |radius|, **|attributes|)

    Arguments:

    |point1|, |point2| -- the end points of the cylinder axis (vectors)

    |radius| -- the radius  (a positive number)

    |attributes| -- any graphics object attribute
    """

    def __init__(self, point1, point2, radius, **attr):
        self.point1 = point1
        self.point2 = point2
        self.radius = radius
        ShapeObject.__init__(self, attr)

    # accept "faces" for compatibility with VRML module
    attribute_names = ShapeObject.attribute_names + ['faces']

    def show(self, window):
        self.object = visual.cylinder(pos = tuple(self.point1),
                                      axis = tuple(self.point2-self.point1),
                                      radius = self.radius)

class Arrow(ShapeObject):

    """Arrow

    Constructor: Arrow(|point1|, |point2|, |radius|, **|attributes|)

    Arguments:

    |point1|, |point2| -- the end points of the cylinder axis (vectors)

    |radius| -- the radius  (a positive number)

    |attributes| -- any graphics object attribute
    """

    def __init__(self, point1, point2, radius, **attr):
        self.point1 = point1
        self.point2 = point2
        self.radius = radius
        ShapeObject.__init__(self, attr)

    def show(self, window):
        self.object = visual.arrow(pos = tuple(self.point1),
                                   axis = tuple(self.point2-self.point1),
                                   shaftwidth = self.radius)


class Cone(ShapeObject):

    """Cone

    Constructor: Cone(|point1|, |point2|, |radius|, **|attributes|)

    Arguments:

    |point1|, |point2| -- the end points of the cylinder axis (vectors).
                          |point1| is the tip of the cone.

    |radius| -- the radius  (a positive number)

    |attributes| -- any graphics object attribute
    """

    def __init__(self, point1, point2, radius, face = 1, **attr):
        self.point1 = point1
        self.point2 = point2
        self.radius = radius
        ShapeObject.__init__(self, attr)

    # accept "face" for compatibility with VRML module
    attribute_names = ShapeObject.attribute_names + ['face']

    def show(self, window):
        self.object = visual.cone(pos = tuple(self.point2),
                                  axis = tuple(self.point1-self.point2),
                                  radius = self.radius)

class PolyLines(ShapeObject):

    """Multiple connected lines

    Constructor: PolyLines(|points|, **|attributes|)

    Arguments:

    |points| -- a sequence of points to be connected by lines

    |attributes| -- any graphics object attribute
    """

    def __init__(self, points, **attr):
        self.points = points
        ShapeObject.__init__(self, attr)

    def show(self, window):
        self.object = visual.curve(pos = map(tuple, self.points),
                                   color = window.foreground)


class Line(PolyLines):

    """Line

    Constructor: Line(|point1|, |point2|, **|attributes|)

    Arguments:

    |point1|, |point2| -- the end points of the line (vectors)

    |attributes| -- any graphics object attribute
    """

    def __init__(self, point1, point2, **attr):
        apply(PolyLines.__init__, (self, [point1, point2]), attr)


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
        ShapeObject.__init__(self, attr)

    def show(self, window):
        for indices in self.index_lists:
            points = []
            for index in indices:
                points.append(tuple(self.points[index]))
            visual.convex(pos = points, color = window.foreground)

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

    def show(self, window):
        for o in self.objects:
            o.show(window)


def isGroup(x):
    return hasattr(x, 'is_group')


#
# Materials
#
class Material(GraphicsObject):

    """Material for graphics objects

    A material defines the color and surface properties of an object.

    Constructor: Material(**|attributes|)

    The attributes are "ambient_color", "diffuse_color", "specular_color",
    "emissive_color", "shininess", and "transparency".
    """

    def __init__(self, **attr):
        GraphicsObject.__init__(self, attr)

    attribute_names = GraphicsObject.attribute_names + \
                      ['ambient_color', 'diffuse_color', 'specular_color',
                       'emissive_color', 'shininess', 'transparency']

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

    if 0:
        spheres = EmissiveMaterial('blue')
        links = EmissiveMaterial('orange')
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
        scale = ColorScale(10.)
        for x in range(11):
            color = scale(x)
            m = Material(diffuse_color = color)
            scene.addObject(Cube(Vector(x,0.,0.), 0.2, material=m))
        scene.view()

    if 1:
        points = [Vector(0., 0., 0.),
                  Vector(0., 1., 0.),
                  Vector(1., 1., 0.),
                  Vector(1., 0., 0.),
                  Vector(1., 0., 1.),
                  Vector(1., 1., 1.)]
        indices = [[0, 1, 2, 3, 0], [3, 4, 5, 2, 3]]
        scene = Scene(Polygons(points, indices,
                               material=EmissiveMaterial('blue')))
        scene.view()

    if 0:
        points = [Vector(0., 0., 0.),
                  Vector(0., 1., 0.),
                  Vector(1., 1., 0.),
                  Vector(1., 0., 0.),
                  Vector(1., 0., 1.),
                  Vector(1., 1., 1.)]
        scene = Scene(PolyLines(points, material = EmissiveMaterial('green')))
        scene.view()
