"""Reduced route guard and finite-graph negative cycles, not global GR proofs."""
import math
from .contracts import number
from .physics import C


def route_guard(external, internal, offset, u_external=0, u_internal=0,
                u_offset=0, policy=0):
    for name, value in {"external": external, "internal": internal,
                        "u_external": u_external, "u_internal": u_internal,
                        "u_offset": u_offset, "policy": policy}.items():
        number(value, name, 0, 1e15)
    number(offset, "offset", -1e15, 1e15)
    raw = math.fsum([external, internal, -abs(offset)])
    safe = math.fsum([external, internal, -abs(offset), -u_external, -u_internal, -u_offset, -policy])
    status = "FAIL" if raw < 0 else "CRITICAL" if safe <= 0 else "PASS"
    return {"raw_margin_s": raw, "safe_margin_s": safe, "status": status,
            "action": "LOCKOUT" if raw < 0 else "CLOSE" if safe <= 0 else "ALLOW_ANALOG",
            "scope": "REDUCED_TWO_ROUTE", "global_certificate": "UNRESOLVED"}


def covariance_bound(covariance, z=3.0):
    """Simultaneous component bounds using a declared multiplier.

    Validate positive semidefiniteness by principal minors (3x3 symmetric).
    z*sum(sigma_i) bounds any correlations conditional on each component bound.
    No automatic confidence claim: Gaussian/coverage assumptions are external.
    """
    number(z, "z", 0, 10)
    if len(covariance) != 3 or any(len(row) != 3 for row in covariance):
        raise ValueError("covariance must be 3x3 in seconds squared")
    a = [[number(v, "covariance entry", -1e30, 1e30) for v in row] for row in covariance]
    scale = max(abs(v) for row in a for v in row)
    if scale == 0:
        return {"bound_s": 0.0, "coverage": "NOT_AUTOMATICALLY_CERTIFIED"}
    b = [[v/scale for v in row] for row in a]
    for i in range(3):
        if a[i][i] < 0:
            raise ValueError("negative variance")
        for j in range(3):
            if abs(b[i][j]-b[j][i]) > 1e-12:
                raise ValueError("covariance must be symmetric")
            if b[i][i]*b[j][j]-b[i][j]**2 < -1e-12:
                raise ValueError("covariance is not positive semidefinite")
    det = (b[0][0]*(b[1][1]*b[2][2]-b[1][2]**2)
           -b[0][1]*(b[0][1]*b[2][2]-b[0][2]*b[1][2])
           +b[0][2]*(b[0][1]*b[1][2]-b[0][2]*b[1][1]))
    if det < -1e-12:
        raise ValueError("covariance is not positive semidefinite")
    return {"bound_s": z*sum(math.sqrt(a[i][i]) for i in range(3)),
            "coverage": "CONDITIONAL_ON_SIMULTANEOUS_COMPONENT_BOUNDS"}


def clock_offset(duration_s, speed_m_s):
    number(duration_s, "duration_s", 0, 1e15)
    number(speed_m_s, "speed_m_s", 0, C*(1-1e-12))
    beta2 = (speed_m_s/C)**2
    # Stable when v/c is tiny: avoid 1-sqrt(1-beta^2) cancellation.
    return duration_s*beta2/(1+math.sqrt(1-beta2))


def negative_cycle(nodes, edges):
    """Bellman-Ford over explicitly supplied travel-time edges.

    A witness is only in this graph; no witness never certifies spacetime.
    Zero-weight cycles are outside this strict negative-cycle test.
    """
    if not 1 <= len(nodes) <= 100 or len(nodes) != len(set(nodes)):
        raise ValueError("1..100 unique nodes required")
    if len(edges) > 2000:
        raise ValueError("too many edges")
    d, previous = dict.fromkeys(nodes, 0.0), {}
    for e in edges:
        if set(e) != {"from", "to", "time_s"} or e["from"] not in d or e["to"] not in d:
            raise ValueError("invalid graph edge")
        number(e["time_s"], "edge time", -1e15, 1e15)
    changed = None
    for _ in nodes:
        changed = None
        for index, e in enumerate(edges):
            if d[e["to"]] > d[e["from"]]+e["time_s"]:
                d[e["to"]] = d[e["from"]]+e["time_s"]
                previous[e["to"]] = index
                changed = e["to"]
        if changed is None:
            return {"status": "UNRESOLVED", "negative_cycle": None,
                    "scope": "FINITE_ROUTE_GRAPH", "global_certificate": False}
    for _ in nodes:
        changed = edges[previous[changed]]["from"]
    start, cycle = changed, []
    while True:
        edge = edges[previous[changed]]
        cycle.append(edge)
        changed = edge["from"]
        if changed == start:
            break
    cycle.reverse()
    return {"status": "FAIL", "negative_cycle": cycle,
            "total_time_s": sum(e["time_s"] for e in cycle),
            "scope": "FINITE_ROUTE_GRAPH", "global_certificate": False}
