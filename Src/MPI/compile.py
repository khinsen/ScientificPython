# Compile the mpipython executable containing
# the Scientific.MPI extension module

# Normally nothing needs to be changed below
import distutils
import distutils.sysconfig
import os  

cfgDict = distutils.sysconfig.get_config_vars()

# Name of the MPI compilation script.
mpicompiler = 'mpicc'
sources='mpipython.c Scientific_mpi.c'


cmd = '%s %s -o mpipython -I%s %s -L%s -lpython%s %s %s' % \
    (mpicompiler, 
    cfgDict['LINKFORSHARED'],
    cfgDict['INCLUDEPY'],
    sources,
    cfgDict['LIBPL'],
    cfgDict['VERSION'], 
    cfgDict['LIBS'], 
    cfgDict['LIBM'])

print 'cmd = ', cmd 
os.system(cmd)
