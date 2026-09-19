"""Numerical-relativity output assessment, not a model-specific NR solver."""
import csv
import io
import math
from .contracts import number


def assess_constraints(text):
    """Each row: resolution_h,H_L2,M_L2, same physical time/domain/gauge.

    Assumptions cannot be verified from three norms. This is a consistency
    diagnostic; incoming numerical data never unlocks physical PA gates.
    """
    if len(text.encode()) > 100_000:
        raise ValueError("constraint CSV too large")
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    if set(reader.fieldnames or []) != {"resolution_h", "H_L2", "M_L2"}:
        raise ValueError("require exactly resolution_h,H_L2,M_L2")
    for row in reader:
        rows.append({k: number(float(v), k, 1e-100, 1e100) for k, v in row.items()})
        if len(rows) > 30:
            raise ValueError("maximum 30 resolutions")
    if len(rows) < 3:
        raise ValueError("at least three distinct resolutions required")
    rows.sort(key=lambda r: r["resolution_h"], reverse=True)
    if len({r["resolution_h"] for r in rows}) != len(rows):
        raise ValueError("duplicate resolution")
    orders = []
    for coarse, fine in zip(rows, rows[1:]):
        ratio = coarse["resolution_h"]/fine["resolution_h"]
        orders.append({key: math.log(coarse[key]/fine[key])/math.log(ratio) for key in ("H_L2", "M_L2")})
    return {"scope": "EXTERNAL_CONSTRAINT_NORMS_ONLY", "rows": rows, "orders": orders,
            "decreasing": all(p[k] > 0 for p in orders for k in p),
            "input_origin": "USER_SUPPLIED_UNVERIFIED", "physical_gate_status": "UNRESOLVED",
            "assumptions": ["same physical time", "same domain and norms", "consistent formulation",
                            "asymptotic refinement regime"],
            "missing": ["model-specific coupled field evolution", "formation", "boundary sweep",
                        "gauge sweep", "payload perturbations", "independent solver"]}
