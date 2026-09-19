"""Derive connection, Ricci and Einstein tensors from the metric using SymPy.

The derivation is algorithmic and separate from the analytical SI formulas.
This is not a second independent laboratory/team or a general topology engine.
"""
from functools import lru_cache


@lru_cache(maxsize=3)
def derive(model="M04"):
    import sympy as s
    t, l, theta, phi = s.symbols("ct l theta phi", real=True)
    a, mass = s.symbols("a M", positive=True)
    coords = (t, l, theta, phi)
    if model == "M04":
        metric = s.diag(-1, 1, l*l+a*a, (l*l+a*a)*s.sin(theta)**2)
    elif model == "M00":
        metric = s.diag(-1, 1, 1, 1)
    elif model == "M01":
        f = 1-2*mass/l
        metric = s.diag(-f, 1/f, l*l, l*l*s.sin(theta)**2)
    else:
        raise ValueError("symbolic engine supports M00, M01, M04")
    inv = metric.inv()
    gamma = [[[s.simplify(sum(inv[i, d]*(s.diff(metric[d, k], coords[j])
                 +s.diff(metric[d, j], coords[k])-s.diff(metric[j, k], coords[d]))
                 for d in range(4))/2) for k in range(4)] for j in range(4)] for i in range(4)]
    riemann = {}
    # R^i_jkl = d_k Gamma^i_lj - d_l Gamma^i_kj + Gamma^i_km Gamma^m_lj - ...
    for i in range(4):
        for j in range(4):
            for k in range(4):
                for n in range(4):
                    value = s.simplify(s.diff(gamma[i][n][j], coords[k])
                        - s.diff(gamma[i][k][j], coords[n])
                        + sum(gamma[i][k][m]*gamma[m][n][j]
                              - gamma[i][n][m]*gamma[m][k][j] for m in range(4)))
                    if value != 0:
                        riemann[(i, j, k, n)] = value
    ricci = s.zeros(4)
    for i in range(4):
        for j in range(4):
            ricci[i, j] = s.simplify(sum(
                s.diff(gamma[k][i][j], coords[k])-s.diff(gamma[k][i][k], coords[j])
                +sum(gamma[k][i][j]*gamma[m][k][m]-gamma[m][i][k]*gamma[k][j][m]
                     for m in range(4)) for k in range(4)))
    scalar = s.simplify(sum(inv[i, j]*ricci[i, j] for i in range(4) for j in range(4)))
    einstein = s.simplify(ricci-metric*scalar/2)
    if model == "M04":
        r2 = l*l+a*a
        expected = s.diag(-a*a/r2**2, -a*a/r2**2, a*a/r2, a*a*s.sin(theta)**2/r2)
        scalar_expected = -2*a*a/r2**2
    else:
        expected, scalar_expected = s.zeros(4), s.Integer(0)
    checks = {"inverse": s.simplify(metric*inv-s.eye(4)) == s.zeros(4),
              "Ricci_symmetric": ricci == ricci.T,
              "Einstein_components": s.simplify(einstein-expected) == s.zeros(4),
              "scalar": s.simplify(scalar-scalar_expected) == 0}
    ricci_from_riemann = s.Matrix(4, 4, lambda j, n: s.simplify(sum(
        riemann.get((i, j, i, n), 0) for i in range(4))))
    checks["Riemann_Ricci_contraction"] = s.simplify(ricci-ricci_from_riemann) == s.zeros(4)
    kretschmann = s.simplify(sum(metric[i, i]*inv[j, j]*inv[k, k]*inv[n, n]*v*v
                                for (i, j, k, n), v in riemann.items()))
    expected_K = 12*a**4/(l*l+a*a)**4 if model == "M04" else 48*mass**2/l**6 if model == "M01" else 0
    checks["Kretschmann"] = s.simplify(kretschmann-expected_K) == 0
    divergence = []
    mixed = inv*einstein
    for j in range(4):
        divergence.append(s.simplify(sum(s.diff(mixed[i, j], coords[i])
            +sum(gamma[i][i][k]*mixed[k, j]-gamma[k][i][j]*mixed[i, k] for k in range(4))
            for i in range(4))))
    checks["contracted_Bianchi"] = all(v == 0 for v in divergence)
    return {"model_id": model, "units": "geometrized; x0=ct", "signature": "-+++",
            "metric": [[str(v) for v in row] for row in metric.tolist()],
            "ricci": [[str(v) for v in row] for row in ricci.tolist()],
            "einstein": [[str(v) for v in row] for row in einstein.tolist()],
            "ricci_scalar": str(scalar), "determinant": str(s.simplify(metric.det())),
            "kretschmann": str(kretschmann),
            "nonzero_riemann": {','.join(map(str, indices)): str(v) for indices, v in riemann.items()},
            "nonzero_connection": {f"{i},{j},{k}": str(gamma[i][j][k])
                for i in range(4) for j in range(4) for k in range(4) if gamma[i][j][k] != 0},
            "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL",
            "scope": "LOCAL_SYMBOLIC_GEOMETRY"}
