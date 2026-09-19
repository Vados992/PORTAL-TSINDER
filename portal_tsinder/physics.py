"""M04 in SI, signature (-,+,+,+); x^0=ct for tensor components.

Static geometry does not determine a realizable material source. The volume
integral is a diagnostic, never an ADM mass or an actuator energy budget.
"""
import math
from .contracts import number

C = 299_792_458.0
G = 6.67430e-11
HBAR = 1.054571817e-34
KAPPA = 8 * math.pi * G / C**4


def domain(r, a):
    number(a, "throat radius", 1e-12, 1e12)
    number(r, "areal radius", a, 1e15)


def areal_radius(l, a):
    number(l, "proper radius", -1e15, 1e15)
    domain(a, a)
    return math.hypot(l, a)


def shape(r, a):
    domain(r, a)
    return a * (a / r)


def proper_distance(r, a):
    domain(r, a)
    return math.sqrt((r - a) * (r + a))


def embedding(r, a):
    domain(r, a)
    return a * math.acosh(r / a)


def stress(r, a):
    domain(r, a)
    scale = (a / r)**2 / (r*r*KAPPA)
    return {"rho_J_m3": -scale, "p_radial_Pa": -scale,
            "p_tangential_Pa": scale, "radial_NEC_J_m3": -2*scale,
            "tangential_NEC_J_m3": 0.0}


def invariants(l, a):
    r = areal_radius(l, a)
    k = (a / r)**2 / r**2
    return {"ricci_scalar_m2": -2*k, "ricci_squared_m4": 4*k*k,
            "kretschmann_m4": 12*k*k}


def volume_energy(r, a):
    domain(r, a)
    return -C**4*a/G * math.atan2(proper_distance(r, a), a)


def volume_energy_limit(a):
    domain(a, a)
    return -math.pi*C**4*a/(2*G)


def traversal(r, a, beta):
    domain(r, a)
    number(beta, "speed fraction c", 1e-12, 0.999999999)
    length = 2*proper_distance(r, a)
    t = length / (beta*C)
    return {"length_m": length, "coordinate_time_s": t,
            "proper_time_s": t*math.sqrt((1-beta)*(1+beta)),
            "null_time_s": length/C}


def radial_traveler_tides(l, a, beta, separation):
    """Boosted orthonormal frame; radial eigenvalue=0, two transverse ones.

    R_0202'= -gamma^2 beta^2 a^2/(l^2+a^2)^2 (up to Riemann sign);
    acceleration magnitude is c^2 |R_0202'| separation.
    """
    number(beta, "beta", 0, 0.999999999)
    number(separation, "separation", 0, 1e12)
    r = areal_radius(l, a)
    curvature = beta**2 / ((1-beta)*(1+beta)) * (a/r)**2 / r**2
    return {"radial_m_s2": 0.0, "transverse_m_s2": C*C*curvature*separation,
            "transverse_curvature_m2": curvature}


def phantom_source(l, a):
    """Formal Ellis ghost scalar in geometrized units, NOT ordinary matter.

    L=+1/2 (grad phi)^2; phi=atan(l/a)/sqrt(4pi), negative kinetic energy.
    T_ab=-d_a phi d_b phi + g_ab (grad phi)^2/2.
    """
    r = areal_radius(l, a)
    derivative = a/(math.sqrt(4*math.pi)*r*r)
    d2 = -2*a*l/(math.sqrt(4*math.pi)*r**4)
    rho = -0.5*derivative**2
    spatial_R = -2*a*a/r**4
    return {"phi": math.atan(l/a)/math.sqrt(4*math.pi),
            "rho_geometric_m2": rho,
            "klein_gordon_residual_m2": d2+2*l/(r*r)*derivative,
            "ADM_Hamiltonian_residual_m2": spatial_R-16*math.pi*rho,
            "ADM_momentum_residual": 0.0,
            "source_kind": "FORMAL_GHOST_SCALAR", "physical_admissibility": "UNRESOLVED",
            "negative_kinetic_energy": True, "formation_history": "UNRESOLVED"}


def schwarzschild(r_m, mass_kg):
    number(mass_kg, "mass_kg", 1e-12, 1e45)
    number(r_m, "r_m", 1e-12, 1e30)
    rs = 2*G*mass_kg/C**2
    return {"model_id": "M01", "schwarzschild_radius_m": rs,
            "lapse_squared": 1-rs/r_m,
            "kretschmann_m4": 12*rs*rs/r_m**6,
            "exterior_chart_valid": r_m > rs,
            "bridge_traversability": "FAIL"}
