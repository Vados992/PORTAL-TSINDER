"""Explicit second-order test-field solver on a fixed M04 background.

For scalar Phi=psi(t,l)Y_lm/r(l): psi_tt=psi_ll-V psi-2*damping*psi_t,
V=ell(ell+1)/(l^2+a^2)+a^2/(l^2+a^2)^2. Computation uses a=c=1.
Dirichlet endpoints reflect waves; they are not absorbing asymptotic boundaries.
No metric evolution, source evolution or nonlinear GR stability is inferred.
"""
import math
from .contracts import number, integer


def solve(model="M04", points=201, extent=10.0, duration=6.0, ell=0,
          damping=0.0, cfl=0.5, initial="gaussian"):
    if model not in ("M00", "M04") or initial not in ("gaussian", "sine"):
        raise ValueError("supported models M00/M04, initial gaussian/sine")
    integer(points, "points", 33, 501)
    integer(ell, "ell", 0, 8)
    number(extent, "extent", 2, 50)
    number(duration, "duration", 0.01, 30)
    number(damping, "damping", 0, 2)
    number(cfl, "cfl", 0.05, 0.9)
    dx = 2*extent/(points-1)
    x = [-extent+i*dx for i in range(points)]
    potential = [0.0 if model == "M00" else ell*(ell+1)/(1+v*v)+1/(1+v*v)**2 for v in x]
    limit = 2/math.sqrt(4/dx**2+max(potential))
    steps = math.ceil(duration/(cfl*limit))
    if steps*points > 1_500_000:
        raise ValueError("wave computation budget exceeded; reduce resolution/duration")
    dt = duration/steps
    if initial == "sine":
        u = [math.sin(math.pi*(v+extent)/(2*extent)) for v in x]
        velocity = [0.0]*points
    else:
        center, width = -extent/2, 0.7
        u = [math.exp(-(v-center)**2/(2*width*width)) for v in x]
        velocity = [(v-center)/width**2*a for v, a in zip(x, u)]
    u[0] = u[-1] = 0.0
    velocity[0] = velocity[-1] = 0.0
    def acceleration(arr):
        return [0.0]+[(arr[i+1]-2*arr[i]+arr[i-1])/dx**2-potential[i]*arr[i]
                      for i in range(1, points-1)]+[0.0]
    acc = acceleration(u)
    prev = [v-dt*w+0.5*dt*dt*(a-2*damping*w) for v, w, a in zip(u, velocity, acc)]
    snapshots, energies, detector = [], [], []
    def discrete_energy(left, right):
        kinetic = sum(((b-a)/dt)**2 for a, b in zip(left, right))
        gradient = sum((left[i+1]-left[i])*(right[i+1]-right[i])/dx**2 for i in range(points-1))
        mass = sum(v*a*b for v, a, b in zip(potential, left, right))
        return 0.5*dx*(kinetic+gradient+mass)
    energy0 = discrete_energy(prev, u)
    for step in range(steps+1):
        e = discrete_energy(prev, u)
        if step % max(1, steps//100) == 0 or step == steps:
            energies.append({"time": step*dt, "energy": e})
            detector.append({"time": step*dt, "left": u[points//4], "right": u[3*points//4]})
        if step % max(1, steps//20) == 0 or step == steps:
            snapshots.append({"time": step*dt, "psi": u[:]})
        if step == steps:
            break
        acc = acceleration(u)
        nxt = [(2*u[i]-(1-damping*dt)*prev[i]+dt*dt*acc[i])/(1+damping*dt)
               for i in range(points)]
        nxt[0] = nxt[-1] = 0.0
        if any(not math.isfinite(v) or abs(v) > 1e12 for v in nxt):
            raise ValueError("wave integration diverged")
        prev, u = u, nxt
    exact_error = None
    if model == "M00" and initial == "sine" and damping == 0:
        exact = [math.sin(math.pi*(v+extent)/(2*extent))*math.cos(math.pi*duration/(2*extent)) for v in x]
        exact_error = math.sqrt(dx*sum((v-w)**2 for v, w in zip(u, exact)))
    return {"scope": "LINEAR_TEST_FIELD_FIXED_BACKGROUND", "model_id": model,
            "boundary": "REFLECTING_DIRICHLET", "coordinates": "l/a and ct/a",
            "steps": steps, "dx": dx, "dt": dt, "CFL": dt/dx,
            "x": x, "potential": potential, "final": u, "snapshots": snapshots,
            "energy": energies, "detector": detector, "analytic_L2_error": exact_error,
            "relative_energy_drift": (energies[-1]["energy"]-energy0)/energy0,
            "nonlinear_spacetime_stability": "UNRESOLVED"}


def convergence():
    rows = []
    for points in (65, 129, 257):
        result = solve("M00", points, 4, 3, initial="sine")
        rows.append({"points": points, "dx": result["dx"], "L2": result["analytic_L2_error"]})
    orders = [math.log(a["L2"]/b["L2"], 2) for a, b in zip(rows, rows[1:])]
    return {"scope": "M00_LINEAR_WAVE_MANUFACTURED_SOLUTION", "grids": rows,
            "orders": orders, "status": "PASS" if min(orders) > 1.8 else "FAIL"}
