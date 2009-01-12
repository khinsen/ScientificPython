# Compile the bsppython executable containing
# the Scientific.BSPlib extension module
# using the BSPonMPI library (http://bsponmpi.sourceforge.net/)

# Normally nothing needs to be changed below
import distutils
import distutils.sysconfig
import os, sys
from Scientific import N

cfgDict = distutils.sysconfig.get_config_vars()

# Name of the MPI compilation script.
mpicompiler = 'mpicc'
sources='bsppython.c Scientific_bsplib.c'

extra_compile_args = ""
if N.package == "NumPy":
    arrayobject_h_include = os.path.join(sys.prefix,
                            "lib/python%s.%s/site-packages/numpy/core/include"
                                          % sys.version_info [:2])
    extra_compile_args = "-DNUMPY=1 -I"+arrayobject_h_include

linkforshared = cfgDict['LINKFORSHARED']
if sys.platform == 'darwin':
    # Fix LINKFORSHARED for framework builds under MacOS
    items = linkforshared.split()
    frameworkdir = (sys.prefix, '')
    while frameworkdir[1] != 'Python.framework':
        frameworkdir = os.path.split(frameworkdir[0])
    for i in range(len(items)):
        if 'Python.framework' in items[i] and not os.path.exists(items[i]):
            items[i] = os.path.join(frameworkdir[0], items[i])
    linkforshared = ' '.join(items)

cmd = '%s %s -o bsppython -I%s %s %s -L%s -lpython%s -lbsponmpi %s %s' % \
    (mpicompiler, 
     linkforshared,
     cfgDict['INCLUDEPY'],
     extra_compile_args,
     sources,
     cfgDict['LIBPL'],
     cfgDict['VERSION'], 
     cfgDict['LIBS'], 
     cfgDict['LIBM'])

print 'cmd = ', cmd 
os.system(cmd)
