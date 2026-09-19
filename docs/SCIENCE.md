# Mathematical implementation and scope

The normative starting point is the user-supplied PORTAL-FA v1.0 document,
Document ID `PORTAL-FA-2026-V1.0-RU-0901-VT`.
Source PDF SHA-256:
`89c7050392fbe7b52f7293288bb26f5a365d7cffcf5d4f0f6be880d0e9052a1c`.
The original PDF is not redistributed in this repository. Source code was written
for this workbench; it is not represented as a byte-identical extraction of the
document's reference kernel. The software version is independent of PDF version.

## M04 conventions

SI constants: c=299792458 m/s, G=6.67430e-11 m³ kg⁻¹ s⁻²,
hbar=1.054571817e-34 J s. G is a measured value, hbar here is rounded.
Signature (-,+,+,+), x⁰=ct. The symbolic M01 calculation uses geometrized mass M.
The proper radial chart avoids the areal-coordinate singularity at the throat:

`ds² = -c² dt² + dl² + (l²+a²) dΩ²`, `r(l)=sqrt(l²+a²)`, `a>0`.

The declared manifold is R_t × R_l × S², with two ends l→±∞, no time
identification, and ordinary sphere coordinate patches. This is a fixed topology
specification, not a general quotient/gluing engine. The global time function of
this exact unshifted static ansatz is not a certificate for arbitrary moving-mouth
device geometries. The application does not promote G12 from it.

Derived quantities:

- b(r)=a²/r, b'(a)=-1, flare-out margin 2.
- R=-2a²/(l²+a²)²; Ricci²=4a⁴/(l²+a²)⁴; K=12a⁴/(l²+a²)⁴.
- rho=p_r=-c⁴a²/(8πG r⁴); p_t=+c⁴a²/(8πG r⁴).
- Radial NEC: rho+p_r<0. Tangential contraction: rho+p_t=0.
- Two-sided proper volume energy through cutoff R:
  `E=-(c⁴a/G) atan(sqrt(R²-a²)/a)`.
- Limit R→∞: `-πc⁴a/(2G)`. ADM mass is zero for this massless ansatz.

The volume diagnostic is not a battery energy, engineering cost, or ADM mass.
The Python implementation also computes an independent proper-coordinate Simpson
integral in tests. Radius scaling, signs and factors are checked.

## Tensors and residuals

`symbolic.py` differentiates the metric, builds Gamma, Riemann, Ricci, scalar R,
Einstein tensor and Kretschmann, then checks inversion, symmetry, contracted Bianchi,
Ricci/Riemann contraction and known analytical values. M00 and exterior M01 are
negative/control models. These are separate calculation paths within one codebase;
they are not independent-team replication or a second CAS.

`physics.phantom_source` supplies the restricted massless Ellis ghost scalar:
phi=atan(l/a)/sqrt(4π), L=+1/2(grad phi)², geometrized G=c=1.
Its negative kinetic energy gives rho=-phi'²/2. The massless wave equation and
time-symmetric ADM Hamiltonian constraint R³=16πrho are checked. Momentum is zero.
This is formal source consistency, not physical source admissibility or formation.

## Geodesics and tides

Set x=l/a and dimensionless affine coordinate s/a (s=cτ for a massive test
particle). Equatorial geodesics obey:

`x''=J²x/(1+x²)²`, `phi'=J/(1+x²)`, `(ct/a)'=E`.

RK4 integrates both signs of radial motion, including angular reflection.
The invariant is `-E²+x'²+J²/(1+x²)=-epsilon`, epsilon=1 timelike/0 null.
Initial E/J come from the local static orthonormal frame. Reports include maximum
normalization error and explicitly reject excessive step size. Crossing the
throat during the finite integration is reported; arbitrary late escape is not.

For a radial traveler, static time-space curvature vanishes but the Lorentz-boosted
transverse component has magnitude `gamma² beta² a²/(l²+a²)²`.
Multiply by c² times a transverse separation to obtain acceleration magnitude.
At the throat with a=1 m, beta=.01, separation=2 m the default candidate fails
the specified 1-g tidal threshold. Clearance is a separate gate.
No finite-mass payload backreaction, biology, radiation or thermal safety is solved.

## Linear waves

For a massless scalar test field Phi=psi(t,l)Y_ell,m/r(l), set a=c=1:

`psi_tt = psi_ll - V psi - 2 d psi_t`,
`V=ell(ell+1)/(1+l²)+1/(1+l²)²` for M04, V=0 for M00.

Centered space and time differences yield second order convergence. The explicit
step satisfies dt < 2/sqrt(4/dx²+max V); user CFL is limited to 0.9.
Initialization uses displacement, velocity and the half acceleration term.
Dirichlet endpoints are reflecting, not asymptotic/absorbing conditions. Increase
the domain or shorten duration before interpreting arrival traces. Spatial index
ell denotes spherical-harmonic degree, while l is the proper radial coordinate.

For zero damping the scheme preserves a staggered quadratic discrete energy,
using the cross product of adjacent time-slice gradients/potentials. This differs
from a naive same-time continuous-energy estimate. The tests validate conservation
and second-order convergence against a standing sine wave in M00 at three grids.
Bounded linear test-field motion is not nonlinear wormhole stability.

## Reduced causality and uncertainty

`m=t_external+t_internal-|offset|`,
`m_safe=m-u_external-u_internal-u_offset-policy`.

The uncertainties are supplied one-sided bounds, not unqualified standard
deviations. Summation uses `math.fsum` to handle cancellation at guard boundaries.
m<0 gives a reduced-model candidate and LOCKOUT; m_safe≤0 gives CLOSE; otherwise
only simulated analog operation is permitted. A C++ implementation includes a
conservative rounding region and is an arithmetic cross-check, not a safety PLC.

The covariance helper checks a symmetric positive semidefinite 3×3 matrix. Its
z·sum(sigma_i) bound is conservative conditional on simultaneous component bounds;
it does not silently assign a confidence probability or ignore correlations.
Bellman–Ford returns explicit negative cycles in a declared finite route graph.
No cycle found gives UNRESOLVED globally. Zero cycles are outside this strict test.

Endpoint clock integration uses piecewise inertial segments. Accelerations,
gravity and clock synchronization are not inferred. HMAC-authenticated endpoint
records identify simulated/signal nodes; they do not establish physical mouths.

## Quantum and metrology

The QEI function is the stated free massless minimally coupled scalar field in
4D Minkowski with inertial Lorentzian sampling and no boundaries:
`rho_sample >= -3 hbar/(32 pi² c³ tau0⁴)`.
The rectangular pulse comparison analytically integrates the sampling weight;
a chosen density history is not a constructed quantum state. Curved-space physical
admissibility remains unresolved. See the primary
[Ford–Roman paper](https://arxiv.org/abs/gr-qc/9510071).

Quantum teleportation uses an eight-amplitude statevector, Bell preparation,
CNOT and H, all four Alice measurement branches and Bob X/Z corrections.
The unconditioned Bob density before receiving two classical bits is I/2.
Optional noise uses rho→(1-p)rho+p I/2, and p=1 gives fidelity 1/2.
This is an information protocol, not SYK dynamics, FTL or transport of matter.

RLGC transfer uses gamma=sqrt((R+iwL)(G+iwC)) and the ABCD matrix of a finite
passive line with matched reference impedance. CSV accepts complex S21 samples.
Group delay is -d phase/dw after nearest-branch phase unwrapping; actual adjacent
phase increments must be below pi or delay aliases are possible. Calibration divides
complex transfers on the same grid. The software does not invent instrument
calibration, measurement uncertainties or experimental observations.

## Primary implementation references

- Supplied PORTAL-FA sections 8–16, 19–28 and appendices C–G.
- [Morris & Thorne (1988)](https://doi.org/10.1119/1.15620).
- [Ellis (1973)](https://doi.org/10.1063/1.1666161).
- [Bennett et al. (1993)](https://doi.org/10.1103/PhysRevLett.70.1895).
- [SymPy differential geometry documentation](https://docs.sympy.org/latest/modules/diffgeom.html).

The full 2026 bibliography copied into the architecture's model descriptions was
not revalidated paper by paper. Those models remain catalog entries unless an
explicit implementation is listed. No general no-go theorem is claimed here.
