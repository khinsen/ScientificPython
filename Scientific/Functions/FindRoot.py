# 'Safe' Newton-Raphson for numerical root-finding
#
# Written by Scott M. Ransom <ransom@cfa.harvard.edu>
# last revision: 14 Nov 98
#
# Cosmetic changes by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 2003-3-31
#

from FirstDerivatives import DerivVar

def newtonRaphson(function, lox, hix, xacc):
    
    """Finds the root of |function| which is bracketed by values
    |lox| and |hix| to an accuracy of +/- |xacc|. The algorithm
    used is a safe version of Newton-Raphson (see page 366 of NR in
    C, 2ed). |function| must be a function of one variable, and may
    only use operations defined for the DerivVar objects in the
    module FirstDerivatives.

    Example:

      >>>from Scientific.Functions.FindRoot import newtonRaphson
      >>>from Numeric import pi, sin, cos
      >>>def func(x):
      >>>    return (2*x*cos(x) - sin(x))*cos(x) - x + pi/4.0
      >>>newtonRaphson(func, 0.0, 1.0, 1.0e-12)

      yields '0.952847864655'.
    """

    maxit = 500
    tmp = function(DerivVar(lox))
    fl = tmp[0]
    tmp = function(DerivVar(hix))
    fh = tmp[0]
    if ((fl > 0.0 and fh > 0.0) or (fl < 0.0 and fh < 0.0)):
        print "Root must be bracketed in newtonRaphson()"
        return None
    if (fl == 0.0): return lox
    if (fh == 0.0): return hix
    if (fl < 0.0):
        xl=lox
        xh=hix
    else:
        xh=lox
        xl=hix
    rts=0.5*(lox+hix)
    dxold=abs(hix-lox)
    dx=dxold
    tmp = function(DerivVar(rts))
    f = tmp[0]
    df = tmp[1][0]
    for j in range(maxit):
        if ((((rts-xh)*df-f)*((rts-xl)*df-f) > 0.0)
            or (abs(2.0*f) > abs(dxold*df))):
            dxold=dx
            dx=0.5*(xh-xl)
            rts=xl+dx
            if (xl == rts): return rts
        else:
            dxold=dx
            dx=f/df
            temp=rts
            rts=rts-dx
            if (temp == rts): return rts
        if (abs(dx) < xacc): return rts
        tmp = function(DerivVar(rts))
        f = tmp[0]
        df = tmp[1][0]
        if (f < 0.0):
            xl=rts
        else:
            xh=rts
    print "Maximum number of iterations exceeded in newtonRaphson()"
    return 0.0

# Test code

if __name__ == '__main__':

    from Scientific.Numeric import pi, sin, cos

    def func(x):
        return ((2*x*cos(x) - sin(x))*cos(x) - x + pi/4.0)
    
    r = newtonRaphson(func, 0.0, 1.0, 1.0e-12)
    theo =  0.9528478646549419474413332
    print ''
    print 'Finding the root (between 0.0 and 1.0) of:'
    print '    (2*x*cos(x) - sin(x))*cos(x) - x + pi/4 = 0'
    print ''
    print 'Safe-style Newton-Raphson gives (xacc = 1.0e-12) =', r
    print 'Theoretical result (correct to all shown digits) = %15.14f' % theo
    print ''
