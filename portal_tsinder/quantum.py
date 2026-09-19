"""Field-specific QEI benchmark and exact three-qubit teleportation simulator."""
import cmath
import math
from .contracts import number
from .physics import HBAR, C


def flat_qei(tau0_s):
    number(tau0_s, "tau0_s", 1e-18, 1e9)
    return {"lower_bound_J_m3": -3*HBAR/(32*math.pi**2*C**3*tau0_s**4),
            "tau0_s": tau0_s, "field": "free_minimally_coupled_massless_scalar_4D",
            "sampling": "Lorentzian_tau0_over_pi_over_tau2_plus_tau0_squared",
            "worldline": "inertial_Minkowski", "boundaries": "none",
            "wormhole_applicability": "UNRESOLVED"}


def sampled_lorentzian_constant_pulse(rho, half_duration_s, tau0_s):
    """Exact integral for a rectangular signed density pulse and zero elsewhere.

    An assigned pulse is not a realizable quantum state. This comparison is
    a necessary benchmark inequality only, never a sufficiency statement.
    """
    number(rho, "rho", -1e90, 1e90)
    number(half_duration_s, "half_duration_s", 0, 1e15)
    result = flat_qei(tau0_s)
    average = rho*2/math.pi*math.atan(half_duration_s/tau0_s)
    result.update(sampled_density_J_m3=average,
                  benchmark_status="PASS" if average >= result["lower_bound_J_m3"] else "FAIL",
                  quantum_state_admissibility="UNRESOLVED")
    return result


def teleport(theta=1.1, phi=0.7, depolarizing=0.0):
    """Little-endian qubits q0=input, q1=Alice Bell half, q2=Bob.

    Branches are evaluated exactly, not postselected. Corrections X^m1 then
    Z^m0 require two classical bits. Optional Bob depolarizing channel is
    rho -> (1-p) rho + p I/2, applied to each corrected branch.
    """
    number(theta, "theta", 0, math.pi)
    number(phi, "phi", -2*math.pi, 2*math.pi)
    number(depolarizing, "depolarizing", 0, 1)
    target = [math.cos(theta/2), cmath.exp(1j*phi)*math.sin(theta/2)]
    state = [0j]*8
    state[0], state[1] = target
    def h(q):
        nonlocal state
        out = state[:]
        for i in range(8):
            if not (i >> q) & 1:
                j = i | (1 << q)
                out[i] = (state[i]+state[j])/math.sqrt(2)
                out[j] = (state[i]-state[j])/math.sqrt(2)
        state = out
    def cx(control, target_q):
        nonlocal state
        out = [0j]*8
        for i, amplitude in enumerate(state):
            j = i ^ (1 << target_q) if (i >> control) & 1 else i
            out[j] = amplitude
        state = out
    h(1)
    cx(1, 2)
    cx(0, 1)
    h(0)
    before = [[0j, 0j], [0j, 0j]]
    branches = []
    for m0 in range(2):
        for m1 in range(2):
            base = m0 | (m1 << 1)
            pair = [state[base], state[base | 4]]
            probability = sum(abs(v)**2 for v in pair)
            for i in range(2):
                for j in range(2):
                    before[i][j] += pair[i]*pair[j].conjugate()
            pair = [v/math.sqrt(probability) for v in pair]
            if m1:
                pair.reverse()
            if m0:
                pair[1] *= -1
            fidelity = abs(sum(a.conjugate()*b for a, b in zip(target, pair)))**2
            fidelity = (1-depolarizing)*fidelity+depolarizing/2
            branches.append({"alice_bits": [m0, m1], "probability": probability,
                             "corrected_fidelity": fidelity})
    return {"scope": "QUANTUM_INFORMATION_STATEVECTOR", "branches": branches,
            "mean_fidelity": sum(b["probability"]*b["corrected_fidelity"] for b in branches),
            "bob_before_classical_message": [[[v.real, v.imag] for v in row] for row in before],
            "classical_bits_required": 2, "matter_transport": False,
            "spacetime_evidence": False}
