#
# Scientific Python
#


"""
ScientificPython is a collection of Python modules that are useful
for scientific computing. In this collection you will find modules
that cover basic geometry (vectors, tensors, transformations, vector
and tensor fields), quaternions, automatic derivatives, (linear)
interpolation, polynomials, elementary statistics, nonlinear
least-squares fits, unit calculations, Fortran-compatible text
formatting, 3D visualization via VRML, and two Tk widgets for simple
line plots and 3D wireframe models. There are also interfaces to the
netCDF library (portable structured binary files), to MPI (Message
Passing Interface, message-based parallel programming), and to BSPlib
(Bulk Synchronous Parallel programming). For details consult the
manual.

@undocumented: __pkginfo__
@undocumented: LA
@undocumented: N
@undocumented: Mathematica
"""

#
# Package information
#
from __pkginfo__ import __version__

#
# New exception class
#
class IterationCountExceededError(ValueError):

    pass

