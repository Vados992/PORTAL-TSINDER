"""Deterministic RK4 and quadrature with explicit step/domain budgets."""
import math
from .contracts import integer, number


def rk4(rhs, t, y, dt):
    k1 = rhs(t, y)
    k2 = rhs(t+dt/2, [a+dt*b/2 for a, b in zip(y, k1)])
    k3 = rhs(t+dt/2, [a+dt*b/2 for a, b in zip(y, k2)])
    k4 = rhs(t+dt, [a+dt*b for a, b in zip(y, k3)])
    out = [a+dt*(b+2*c+2*d+e)/6 for a, b, c, d, e in zip(y, k1, k2, k3, k4)]
    if any(not math.isfinite(v) for v in out):
        raise ValueError("non-finite integration result")
    return out


def simpson(function, lower, upper, intervals=1000):
    integer(intervals, "intervals", 2, 100000)
    if intervals % 2:
        raise ValueError("Simpson intervals must be even")
    number(lower, "lower")
    number(upper, "upper", lower)
    h = (upper-lower)/intervals
    return h/3*(function(lower)+function(upper)+sum(
        (4 if i % 2 else 2)*function(lower+i*h) for i in range(1, intervals)))


def geodesic(a=1.0, start_l=-5.0, beta=0.6, angular_fraction=0.0,
             kind="timelike", duration=20.0, steps=2000):
    """Equatorial M04 geodesic in dimensionless l/a, s/a, ct/a.

    s=c*tau for timelike trajectories; affine length for null trajectories.
    Conserved E and J set from the local orthonormal initial direction.
    Integrates l''=J^2 l/(l^2+1)^2, phi'=J/(l^2+1), t'=E.
    Physical times returned in SI; numerical path error is monitored by norm.
    """
    from .physics import C
    number(a, "a", 1e-12, 1e12)
    number(start_l, "start_l", -100, 100)
    number(beta, "beta", 1e-8, 0.999999)
    number(angular_fraction, "angular_fraction", -0.999999, 0.999999)
    number(duration, "duration", 1e-6, 200)
    integer(steps, "steps", 10, 20000)
    if kind not in ("null", "timelike"):
        raise ValueError("kind must be null or timelike")
    epsilon = 1 if kind == "timelike" else 0
    E = 1/math.sqrt(1-beta*beta) if epsilon else 1.0
    speed = math.sqrt(E*E-epsilon)
    J = math.hypot(start_l, 1)*speed*angular_fraction
    v = speed*math.sqrt(1-angular_fraction**2)
    if duration/steps*max(E, abs(J), 1) > 0.05:
        raise ValueError("step too large for requested energy/angular momentum; increase steps")
    def rhs(t, y):
        l, radial_v, phi, ct = y
        r2 = 1+l*l
        return [radial_v, J*J*l/r2**2, J/r2, E]
    y = [start_l, v, 0.0, 0.0]
    dt, path, error = duration/steps, [], 0.0
    crossed = False
    for i in range(steps+1):
        norm = -E*E+y[1]**2+J*J/(1+y[0]*y[0])
        error = max(error, abs(norm+epsilon))
        if i % max(1, steps//500) == 0 or i == steps:
            path.append({"affine_m": i*dt*a, "l_m": y[0]*a,
                         "phi_rad": y[2], "coordinate_time_s": y[3]*a/C})
        if i < steps:
            old = y[0]
            y = rk4(rhs, i*dt, y, dt)
            crossed |= old < 0 <= y[0]
    return {"scope": "TEST_GEODESIC_FIXED_M04", "kind": kind, "E": E, "J_over_a": J,
            "normalization_max_error": error, "crossed_throat": crossed,
            "integration_status": "PASS" if error < 1e-6 else "FAIL", "path": path,
            "payload_backreaction": "NOT_INCLUDED"}
