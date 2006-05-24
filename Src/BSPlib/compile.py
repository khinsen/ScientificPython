# Compile the bsppython executable containing
# the Scientific.BSPlib extension module

# this variable controls the level of sanity checking for the BSPlib
# see bspcc -help
bspLibLevel = 2


# Normally nothing needs to be changed below
import distutils
import distutils.sysconfig
import os  


cfgDict = distutils.sysconfig.get_config_vars()


# Name of the BSP compilation script.
bspcompiler = 'bspcc'
sources='bsppython.c Scientific_bsplib.c'


cmd = '%s %s -o bsppython -flibrary-level %d -I%s %s -L%s -lpython%s %s %s' % \
    (bspcompiler, 
    cfgDict['LINKFORSHARED'],
    bspLibLevel, 
    cfgDict['INCLUDEPY'],
    sources,
    cfgDict['LIBPL'],
    cfgDict['VERSION'], 
    cfgDict['LIBS'], 
    cfgDict['LIBM'])

print 'cmd = ', cmd 
os.system(cmd)
