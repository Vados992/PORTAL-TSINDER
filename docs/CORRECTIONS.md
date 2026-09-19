# Changes from the document's reference kernel

The supplied PDF is the architectural source, not proof that all of its proposed
layers are implemented. Its own appendix C describes a deliberately narrow M04
kernel. This release expands the executable software and records these differences.

1. **Evidence flags cannot grant physical PASS.** The original accepts booleans
   such as `source_lagrangian_declared`, `dynamic_stability_replicated` and
   `global_causality_certified`. Its implementation can promote them directly to
   gate PASS. The workbench rejects those inputs and leaves physical gates
   unresolved. Neither uploads nor formal-source algebra grant physical evidence.
2. **No promotion from incomplete prerequisite slices.** The reference's
   `physical_gate_indices` does not include all geometric, clearance and energy
   checks. This release does not use that promotion path at all.
3. **The guard closes at equality.** The appendix's conditional `margin < guard`
   disagrees with the document's uncertainty-safe `m_safe <= 0` rule. This release
   uses the latter and tests the boundary. Stable summation reduces cancellation.
4. **Numbers are finite and strictly typed.** Booleans, NaN, infinities, unknown
   keys, duplicated JSON keys and unsupported model IDs are rejected.
5. **Formal source is not a material solution.** The Ellis ghost action and static
   constraints can be evaluated. The result explicitly exposes negative kinetic
   energy and never becomes a realizable-source approval.
6. **Physical tidal calculation is scoped.** The implementation supplies radial
   traveler-frame transverse tides with the required Lorentz boost, rather than
   labeling an arbitrary coordinate curvature component a payload force.
7. **Causality scopes remain separate.** A finite-graph witness/reduced margin is
   not a global spacetime theorem. An unsuccessful witness search is UNRESOLVED.
8. **Simulation evidence stays simulation evidence.** PID convergence, wave energy
   conservation, Bell-state transfer and S21 delay do not certify a spacetime portal.
9. **Provenance and restart are operational.** Runs are persisted transactionally,
   outputs are hash-addressed, reports export and verify, lockout survives restart,
   and a dirty shutdown requires offline review. This is software integrity, not
   independent physical replication.

These are implementation corrections and scope controls. The original PDF's
claimed kernel SHA is not used as the hash of this different implementation.
