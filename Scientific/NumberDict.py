# Dictionary containing numbers
#
# These objects are meant to be used like arrays with generalized
# indices. Non-existent elements default to zero. Global operations
# are addition, subtraction, and multiplication/division by a scalar.
#
# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 2004-11-22
#

from Scientific import DictWithDefault

class NumberDict(DictWithDefault.DictWithDefault):

    """Dictionary storing numerical values

    Constructor: NumberDict()

    An instance of this class acts like an array of number with
    generalized (non-integer) indices. A value of zero is assumed
    for undefined entries. NumberDict instances support addition,
    and subtraction with other NumberDict instances, and multiplication
    and division by scalars.
    """
    
    def __init__(self):
        DictWithDefault.DictWithDefault.__init__(self, 0)

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return repr(self.data)

    def __coerce__(self, other):
        if type(other) == type({}):
            new = NumberDict()
            new.data = other
            other = new
        return self, other

    def __add__(self, other):
        sum_dict = NumberDict()
        for key in self.keys():
            sum_dict[key] = self[key]
        for key in other.keys():
            sum_dict[key] = sum_dict[key] + other[key]
        return sum_dict

    __radd__ = __add__

    def __sub__(self, other):
        sum_dict = NumberDict()
        for key in self.keys():
            sum_dict[key] = self[key]
        for key in other.keys():
            sum_dict[key] = sum_dict[key] - other[key]
        return sum_dict

    def __rsub__(self, other):
        return other-self

    def __mul__(self, other):
        new = NumberDict()
        for key in self.keys():
            new[key] = other*self[key]
        return new

    __rmul__ = __mul__

    def __div__(self, other):
        new = NumberDict()
        for key in self.keys():
            new[key] = self[key]/other
        return new
