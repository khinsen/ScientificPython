#!/usr/bin/env python

from distutils.core import setup, Extension
from distutils.command.install_headers import install_headers
import os, sys
from glob import glob

# If your netCDF installation is in a non-standard place, set the following
# variable to the base directory, or set the environment variable
# NETCDF_PREFIX before running setup.py
netcdf_prefix = None

class Dummy:
    pass
pkginfo = Dummy()
execfile('Scientific/__pkginfo__.py', pkginfo.__dict__)

extra_compile_args = []
if "--numarray" in sys.argv:
    use_numarray = 1
    extra_compile_args.append("-DNUMARRAY=1")
    sys.argv.remove("--numarray")
else:
    use_numarray = 0

if netcdf_prefix is None:
    try:
        netcdf_prefix=os.environ['NETCDF_PREFIX']
    except KeyError:
        for netcdf_prefix in ['/usr/local', '/usr', '/sw']:
            netcdf_include = os.path.join(netcdf_prefix, 'include')
            netcdf_lib = os.path.join(netcdf_prefix, 'lib')
            if os.path.exists(os.path.join(netcdf_include, 'netcdf.h')):
                break
        else:
            netcdf_prefix = None

if netcdf_prefix is None:
    print "netCDF not found, the netCDF module will not be built!"
    print "If netCDF is installed somewhere on this computer,"
    print "please set NETCDF_PREFIX to the path where"
    print "include/netcdf.h and lib/netcdf.a are located"
    print "and re-run the build procedure."
    ext_modules = []
else:
    print "Using netCDF installation in ", netcdf_prefix
    netcdf_include = os.path.join(netcdf_prefix, 'include')
    netcdf_lib = os.path.join(netcdf_prefix, 'lib')
    ext_modules = [Extension('Scientific_netcdf',
                             ['Src/Scientific_netcdf.c'],
                             include_dirs=['Include', netcdf_include],
                             library_dirs=[netcdf_lib],
                             libraries = ['netcdf'],
                             extra_compile_args=extra_compile_args)]


packages = ['Scientific', 'Scientific.Functions',
            'Scientific.Geometry', 'Scientific.IO',
            'Scientific.Physics', 'Scientific.QtWidgets',
            'Scientific.Statistics', 'Scientific.Signals',
            'Scientific.Threading', 'Scientific.TkWidgets',
            'Scientific.Visualization', 'Scientific.MPI']

ext_modules.append(Extension('Scientific_vector',
                             ['Src/Scientific_vector.c'],
                             libraries=['m']))

if 'sdist' in sys.argv:
    packages.append('Scientific.use_numarray')
    packages.append('Scientific.use_numeric')
elif use_numarray:
    packages.append('Scientific.use_numarray')
else:
    packages.append('Scientific.use_numeric')

if sys.version[:3] >= '2.1':
    packages.append('Scientific.BSP')
    scripts = ['bsp_virtual']
else:
    scripts = []

class modified_install_headers(install_headers):

    def finalize_options(self):
        install_headers.finalize_options(self)
        self.install_dir = \
                os.path.join(os.path.split(self.install_dir)[0], 'Scientific')

headers = glob(os.path.join ("Include","Scientific","*.h"))

setup (name = "ScientificPython",
       version = pkginfo.__version__,
       description = "Various Python modules for scientific computing",
       long_description = 
"""ScientificPython is a collection of Python modules that are useful
for scientific computing. In this collection you will find modules
that cover basic geometry (vectors, tensors, transformations, vector
and tensor fields), quaternions, automatic derivatives, (linear)
interpolation, polynomials, elementary statistics, nonlinear
least-squares fits, unit calculations, Fortran-compatible text
formatting, 3D visualization via VRML, and two Tk widgets for simple
line plots and 3D wireframe models.""",
       author = "Konrad Hinsen",
       author_email = "hinsen@llb.saclay.cea.fr",
       url = "http://dirac.cnrs-orleans.fr/ScientificPython/",
       license = "BSD-like",

       packages = packages,
       headers = headers,
       ext_package = 'Scientific.'+sys.platform,
       ext_modules = ext_modules,
       scripts = scripts,

       cmdclass = {'install_headers': modified_install_headers},
       )
