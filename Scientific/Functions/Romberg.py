# Romberg quadratures for numeric integration.
#
# Written by Scott M. Ransom <ransom@cfa.harvard.edu>
# last revision: 14 Nov 98
#
# Cosmetic changes by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 1999-7-21
#

def trapezoid(function, interval, numtraps):
    """Returns the integral of |function| (a function of one variable)
    over |interval| (a sequence of length two containing the lower and
    upper limit of the integration interval), calculated using the
    trapezoidal rule using |numtraps| trapezoids.

    Example:

      >>>from Scientific.Functions.Romberg import romberg
      >>>from Numeric import pi
      >>>romberg(tan, (0.0, pi/3.0))

      yields '0.693147180562'
    """
    lox, hix = interval
    h = float(hix-lox)/numtraps
    sum = 0.5*(function(lox)+function(hix))
    for i in range(1, numtraps):
        sum = sum + function(lox + i*h)
    return h*sum

def difftrap(function, interval, numtraps):
    # Perform part of the trapezoidal rule to integrate a function.
    # Assume that we had called difftrap with all lower powers-of-2
    # starting with 1.  Calling difftrap only returns the summation
    # of the new ordinates.  It does _not_ multiply by the width
    # of the trapezoids.  This must be performed by the caller.
    #     'function' is the function to evaluate.
    #     'interval' is a sequence with lower and upper limits
    #                of integration.
    #     'numtraps' is the number of trapezoids to use (must be a
    #                power-of-2).
    if numtraps<=0:
        print "numtraps must be > 0 in difftrap()."
        return
    elif numtraps==1:
        return 0.5*(function(interval[0])+function(interval[1]))
    else:
        numtosum = numtraps/2
        h = float(interval[1]-interval[0])/numtosum
        lox = interval[0] + 0.5 * h;
        sum = 0.0
        for i in range(0, numtosum):
            sum = sum + function(lox + i*h)
        return sum

def romberg_diff(b, c, k):
    # Compute the differences for the Romberg quadrature corrections.
    # See Forman Acton's "Real Computing Made Real," p 143.
    tmp = 4.0**k
    return (tmp * c - b)/(tmp - 1.0)

def printresmat(function, interval, resmat):
    # Print the Romberg result matrix.
    i = j = 0
    print 'Romberg integration of', `function`,
    print 'from', interval
    print ''
    print '%6s %9s %9s' % ('Steps', 'StepSize', 'Results')
    for i in range(len(resmat)):
        print '%6d %9f' % (2**i, (interval[1]-interval[0])/(i+1.0)),
        for j in range(i+1):
            print '%9f' % (resmat[i][j]),
        print ''
    print ''
    print 'The final result is', resmat[i][j],
    print 'after', 2**(len(resmat)-1)+1, 'function evaluations.'

def romberg(function, interval, accuracy=1.0E-7, show=0):
    """Returns the integral of |function| (a function of one variable)
    over |interval| (a sequence of length two containing the lower and
    upper limit of the integration interval), calculated using
    Romberg integration up to the specified |accuracy|. If |show| is 1,
    the triangular array of the intermediate results will be printed."""
    i = n = 1
    intrange = interval[1] - interval[0]
    ordsum = difftrap(function, interval, n)
    result = intrange * ordsum
    resmat = [[result]]
    lastresult = result + accuracy * 2.0
    while (abs(result - lastresult) > accuracy):
        n = n * 2
        ordsum = ordsum + difftrap(function, interval, n)
        resmat.append([])
        resmat[i].append(intrange * ordsum / n)
        for k in range(i):
            resmat[i].append(romberg_diff(resmat[i-1][k],
                                          resmat[i][k], k+1))
        result = resmat[i][i]
        lastresult = resmat[i-1][i-1]
        i = i + 1
    if show: printresmat(function, interval, resmat)
    return result

# Test code

if __name__ == '__main__':

    from math import tan, pi
    print ''
    r = romberg(tan, (0.5, 1.0), show=1)
    t = trapezoid(tan, (0.5, 1.0), 1000)
    theo = 0.485042229942291
    print ''
    print 'Trapezoidal rule with 1000 function evaluations  =', t
    print 'Theoretical result (correct to all shown digits) = %15.14f' % theo
    print ''
