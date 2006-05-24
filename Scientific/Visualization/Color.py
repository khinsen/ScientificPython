# This module provides color definitions for use in Visualization.
#
# Written by: Konrad Hinsen <khinsen@cea.fr>
# Last revision: 2005-9-5
#

"""This module provides color definitions that are used in the modules
VRML, VRML2, and VMD.
"""

from Scientific import N
import string

#
# Colors
#
class Color:

    """RGB Color specification

    Constructor: Color(|rgb|), where |rgb| is a sequence of three numbers
    between zero and one, specifying the red, green, and blue intensities.

    Color objects can be added and multiplied with scalars.
    """
    
    def __init__(self, rgb):
        self.rgb = (min(1.,max(0.,rgb[0])),
                    min(1.,max(0.,rgb[1])),
                    min(1.,max(0.,rgb[2])))

    def __mul__(self, scale):
        return Color(map(lambda i, s=scale: s*i, self.rgb))
    __rmul__ = __mul__

    def __add__(self, other):
        return Color(map(lambda a, b: a+b, self.rgb, other.rgb))

    def __cmp__(self, other):
        return cmp(self.rgb, other.rgb)

    def __hash__(self):
        return hash(self.rgb)

    def __str__(self):
        return str(self.rgb[0])+' '+str(self.rgb[1])+' '+str(self.rgb[2])

    def __repr__(self):
        return 'Color(' + repr(self.rgb) + ')'

#
# Color scales
#
class ColorScale:

    """Mapping of a number interval to a color range

    Constructor: ColorScale(|range|), where |range| can be a tuple of
    two numbers (the center of the interval and its width), or a
    single number specifying the widths for a default center of zero.

    Evaluation: colorscale(|number|) returns the Color object
    corresponding to |number|. If |number| is outside the
    predefined interval, the closest extreme value of the interval
    is used.

    The color scale is blue - green - yellow - orange - red.
    """

    def __init__(self, range):
        if type(range) == type(()):
            self.zero, self.range = range
            self.range = self.range-self.zero
        else:
            self.range = range
            self.zero = 0.

    def __call__(self, value):
        value = (value-self.zero)/self.range
        value = max(min(value, 1.), 0.)
        if value <= 0.25:
            red = 0.
            green = 4.*value
            blue = 1.
        elif value <= 0.5:
            red = 0.
            green = 1.
            blue = 1.-4.*(value-0.25)
        elif value <= 0.75:
            red = 4.*(value-0.5)
            green = 1.
            blue = 0.
        else:
            red = 1.
            green = 1.-4.*(value-0.75)
            blue = 0.
        return Color((red, green, blue))

class SymmetricColorScale:

    """Mapping of a symmetric number interval to a color range

    Constructor: SymmetricColorScale(|range|), where |range| is a
    single number defining the interval, which is -|range| to |range|.

    Evaluation: colorscale(|number|) returns the Color object
    corresponding to |number|. If |number| is outside the
    predefined interval, the closest extreme value of the interval
    is used.

    The colors are red for negative numbers and green for positive
    numbers, with a color intensity proportional to the absolute
    value of the argument.
    """

    def __init__(self, max, n = 20):
        self.range = max
        self.n = n
        self.colors = {}

    def __call__(self, value):
        negative = value < 0.
        index = N.floor(abs(value)*self.n/self.range)
        if index > self.n:
            raise ValueError('Value outside range')
        try:
            return self.colors[(negative, index)]
        except KeyError:
            white = 1.*(self.n-index)/self.n
            if negative:
                color = Color((1., white, white))
            else:
                color = Color((white, 1., white))
            self.colors[(negative, index)] = color
            return color

#
# Predefined colors
#
full_colors = {
    'black': Color((0.,0.,0.)),
    'white': Color((1.,1.,1.)),
    'grey': Color((0.5,0.5,0.5)),
    'red': Color((1.,0.,0.)),
    'green': Color((0.,1.,0.)),
    'blue': Color((0.,0.,1.)),
    'yellow': Color((1.,1.,0.)),
    'magenta': Color((1.,0.,1.)),
    'cyan': Color((0.,1.,1.)),
    'orange': Color((1.,0.5,0.)),
    'violet': Color((1.,0.,0.5)),
    'olive': Color((0.1,0.6,0.2)),
    'brown': Color((0.6,0.4,0.)),
    }

dark_colors = {}
for name, value in full_colors.items():
    dark_colors[name] = 0.3*value

light_colors = {}
for name, value in full_colors.items():
    light_colors[name] = 0.7*value + 0.3*full_colors['white']

def ColorByName(name):
    """Returns a Color object corresponding to |name|. The known names
    are black, white, grey, red, green, blue, yellow, magenta, cyan,
    orange, violet, olive, and brown. Any color can be prefixed by
    "light " or "dark " to yield a variant.
    """
    name = string.split(string.lower(name))
    dict = full_colors
    if len(name) == 2:
        if name[0] == 'light':
            dict = light_colors
        elif name[0] == 'dark':
            dict = dark_colors
    return dict[name[-1]]



