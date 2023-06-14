import jax.numpy as np
from jax.numpy import sqrt, copysign, sin
from jax.lax import acos
from jax.scipy import optimize

from rayoptics.util.misc_math import normalize
from rayoptics.raytr.traceerror import TraceError, TraceMissedSurfaceError

from jax.numpy.linalg import norm


def special_dot(d, p): #changed
    return d.dot(p)
        # return d[0] * p[0] + d[1] * p[1] + d[2] * p[2]


def special_p(p0, s, d):                   #changed
    return p0 + s*d
        #return [p0[0] + s * d[0], p0[1] + s * d[1], p0[2] + s * d[2]]

def special_dott(d,p):
    return d[0] * p[0] + d[1] * p[1] + d[2] * p[2]
