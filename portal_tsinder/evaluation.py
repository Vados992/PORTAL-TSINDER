"""G00-G12-compatible reports plus immutable physical-aperture hard stops."""
from .contracts import Candidate, digest
from .physics import (stress, proper_distance, embedding, invariants, traversal,
                      radial_traveler_tides, volume_energy, volume_energy_limit, phantom_source)
from .causality import route_guard

PA_REQUIREMENTS = ["Peer-reviewed realizable source theory", "Independent on-shell solution",
    "State-specific QEI compatibility", "Self-consistent semiclassical backreaction",
    "Regular constructible initial data", "Convergent formation evolution",
    "Nonlinear stability with payload", "Two physical endpoints and worldlines",
    "Global causal certificate", "Preregistered unique observable signature",
    "Independent experimental replication", "Approved facility safety case"]


def evaluate(candidate=None):
    c = candidate or Candidate()
    if isinstance(c, dict):
        c = Candidate.from_dict(c)
    a, r = c.throat_radius_m, c.cutoff_radius_m
    guard = route_guard(c.exterior_travel_time_s, c.wormhole_travel_time_s,
                        c.mouth_time_offset_s, c.uncertainty_external_s,
                        c.uncertainty_internal_s, c.uncertainty_offset_s, c.causal_guard_margin_s)
    s = stress(a, a)
    tides = radial_traveler_tides(0, a, c.speed_fraction_c, c.payload_separation_m)
    gates = []
    def gate(n, title, status, value=None, unit=None, scope="M04 fixed-background benchmark"):
        gates.append({"gate_id": f"G{n:02d}", "title": title, "status": status,
                      "value": value, "unit": unit, "scope": scope})
    gate(0, "Throat identity b(a)=a", "PASS", 0.0, "m")
    gate(1, "Flare-out 1-b'(a)>0", "PASS", 2.0, "dimensionless")
    gate(2, "Finite redshift Phi=0", "PASS", 1.0, "lapse squared")
    gate(3, "Radial null energy condition", "FAIL", s["radial_NEC_J_m3"], "J/m^3")
    gate(4, "Physically admissible source", "UNRESOLVED", scope="Formal ghost scalar is not a realizable source")
    gate(5, "Reduced causal guard", guard["status"], guard["safe_margin_s"], "s",
         "Two-route sufficient margin only; equality closes")
    gate(6, "Initial data and formation history", "UNRESOLVED")
    gate(7, "Nonlinear spacetime stability", "UNRESOLVED")
    gate(8, "State-specific curved-spacetime QEI", "UNRESOLVED")
    gate(9, "Self-consistent semiclassical backreaction", "UNRESOLVED")
    gate(10, "Physical endpoint formation", "UNRESOLVED")
    gate(11, "Payload geometric clearance", "PASS" if c.payload_radius_m < a else "FAIL",
         a-c.payload_radius_m, "m", "Clearance only, no payload safety certification")
    gate(12, "Global causal certificate with endpoint worldlines", "UNRESOLVED")
    gates.append({"gate_id": "TIDAL", "title": "Radial traveler transverse tidal limit at throat",
                  "status": "PASS" if tides["transverse_m_s2"] <= c.tidal_limit_m_s2 else "FAIL",
                  "value": tides["transverse_m_s2"], "unit": "m/s^2",
                  "scope": "Test traveler at specified beta; not full payload dynamics"})
    return {"schema_version": "1.0", "candidate": c.to_dict(), "candidate_sha256": digest(c.to_dict()),
            "highest_claim": "FORMAL_TRAVERSABILITY", "physical_aperture_authorized": False,
            "decision": "GO_PTD0_RESEARCH_ONLY", "physical_decision": "STOP",
            "gates": gates, "causality": guard,
            "physical_gates": [{"gate_id": f"PA-{i:02d}", "title": title,
                                "status": "UNRESOLVED", "action": "STOP"}
                               for i, title in enumerate(PA_REQUIREMENTS)],
            "diagnostics": {"throat_stress": s, "throat_curvature": invariants(0, a),
                "traversal": traversal(r, a, c.speed_fraction_c), "tidal": tides,
                "proper_volume_energy_J": volume_energy(r, a),
                "proper_volume_energy_infinite_J": volume_energy_limit(a),
                "ADM_mass_kg": 0.0, "formal_phantom_source": phantom_source(0, a)},
            "profile": [{"l_m": (i/50-1)*proper_distance(r, a),
                          "r_m": ((i/50-1)**2*proper_distance(r, a)**2+a*a)**0.5}
                         for i in range(101)],
            "limitations": ["No physical actuator, aperture or topology-creation model",
                "Analog stabilization does not stabilize spacetime", "No global causality certificate",
                "Source declaration and uploaded evidence never auto-promote physical gates"]}
