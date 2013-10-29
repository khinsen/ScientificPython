# Implementation of Affinity Propagation in Cython
# Accelerates DataSet.findCluster by a factor of 5.
#
# Written by Konrad Hinsen
#

import numpy as np
cimport numpy as np

def _affinityPropagation(dataset, np.ndarray s, np.ndarray a,
                         np.ndarray r, float damping):
    cdef np.ndarray as
    cdef np.ndarray r_new
    cdef np.ndarray a_new
    cdef np.ndarray rpos
    cdef np.ndarray ind_array
    cdef long *ind
    cdef double *dptr
    cdef double v
    cdef int i
    cdef int j

    as = a + s
    r_new = np.zeros((dataset.nsimilarities,), np.float)
    for i from 0 <= i < dataset.nsimilarities:
        ind_array = dataset.r_update_indices[i]
        ind = <long *>ind_array.data
        dptr = <double *>as.data
        v = dptr[ind[0]]
        for j from 1 <= j < ind_array.shape[0]:
            if dptr[ind[j]] > v:
                v = dptr[ind[j]]
        r_new[i] = s[i] - v
    r = damping*r + (1-damping)*r_new

    rpos = np.maximum(0., r)
    a_new = np.take(r, dataset.a_update_indices_1)
    a_new[-dataset.nitems:] = 0.
    for i from 0 <= i < dataset.nsimilarities:
        ind_array = dataset.a_update_indices_2[i]
        ind = <long *>ind_array.data
        dptr = <double *>rpos.data
        v = dptr[ind[0]]
        for j from 1 <= j < ind_array.shape[0]:
            v = v + dptr[ind[j]]
        a_new[i] = a_new[i] + v
    a_new[:-dataset.nitems] = np.minimum(0., a_new[:-dataset.nitems])
    a = damping*a + (1-damping)*a_new

    return a, r
