# Software architecture

## Execution path

CLI and web submit the same bounded experiment parameters to `service.execute`.
The dispatcher calls actual numerical/analytical modules, then `Store.save_run`
atomically saves canonical input, canonical output and a package fingerprint.
FastAPI serves a static JavaScript interface and authenticated local REST routes.
No front-end-only simulation result is passed off as a server computation.

The live analog controller runs in its own Python thread; experiment requests run
in a bounded thread pool. This reduces accidental coupling in the workbench, but
does not provide process, hardware, electrical or real-time safety isolation.
The C++ executable is independently compiled and tested but is not in the actuator
path. There is no actuator path in this release.

## Package modules

| Module | Responsibility |
|---|---|
| contracts | Strict finite input, canonical JSON, schema data, fingerprints |
| physics / symbolic | Closed forms and tensor derivation |
| numerics / waves | ODE integration and linear PDE experiments |
| evaluation / causality | Scoped gate vector, hard physical stops, reduced route graphs |
| quantum | QEI benchmark and exact information protocol |
| anchors | HMAC signed node records, sequence/freshness checks, worldline diagnostics |
| control / locking | Simulated PID/FSM/watchdog and one-process exclusion |
| metrology / nr | Real CSV analysis, synthetic controls, bounded external solver diagnostics |
| storage / reports | SQL transactions, content-addressed records, audit and exports |
| service / cli / api / web | Interfaces and end-to-end operation |

## Data contracts

Candidate schema is `portal_tsinder/data/candidate.schema.json`; runtime validation
is authoritative and adds cutoff≥throat and finite binary64 numeric range checks.
Unknown fields are rejected, including the PDF's old positive evidence booleans.
Numerical bounds are implementation-domain limits, not new physical constants.

Result fields separate software integrity, mathematical gates and physical gates.
`highest_claim=FORMAL_TRAVERSABILITY` describes the unshifted M04 metric family;
a submitted negative route offset can still produce a separate reduced causal FAIL.
No device GO is implied. `physical_aperture_authorized` is always false.

Model catalog includes all 24 entries from the supplied architecture. Only a
listed module constitutes an implementation; `CATALOG_ONLY` is not executable.
The schema/source registry itself is versioned in Git and included in fingerprints.

SQLite schema is shipped in `data/schema.sql`. Runs point to immutable artifacts;
audit events link the previous hash. SQL triggers prevent accidental update/delete
of artifacts and events. These controls cannot defend against an administrator who
can drop triggers or replace the entire file. An externally retained head anchors
one history snapshot; the application does not claim external attestation.

## Source and numerical precision

All ordinary arithmetic uses Python IEEE-754 binary64. SymPy derives exact
expressions. Deterministic experiments have no random dependency; UUIDs/timestamps
vary, while repeated result JSON from the same environment is reproducible.
The HMAC example creates ephemeral keys and records no secrets. C++ uses long double
and a conservative rounding margin; it may CLOSE earlier than Python close to a
floating boundary. This is documented, not represented as bitwise equivalence.

The package fingerprint covers `.py/.json/.sql/.js/.html/.css` inside
`portal_tsinder`. The release manifest additionally covers tests, native sources,
scripts, docs and packaging. It excludes runtime databases, tokens and build outputs.
Run exports contain the fingerprint, not a copy of every repository source file.

## Threat and failure boundary

The local operator owns the database and can alter local code; the application
does not try to claim protection against its owner. API authentication prevents
ordinary unauthorized remote requests. Host/origin checks reduce rebinding/CSRF,
and browser text insertion avoids user-controlled HTML. No remote code evaluation,
uploaded plugin loading or arbitrary filesystem path is accepted through REST.

One lock prevents concurrent controllers on the same data directory. A dirty
service-start marker is committed before live operation; a clean shutdown clears
it after drive inhibition. A crash causes next-start lockout. A controller storage
exception inhibits simulated output even if logging fails. Review/reset cannot be
called through REST and requires the stopped service's file lock.

The source document calls for an independent safety path, second solver, second
group and hardware evidence before physical claims. This code does not supply or
claim those. A future hardware release needs a separate reviewed safety architecture.

## External software

FastAPI/Starlette/Uvicorn serve the application; SymPy performs symbolic algebra.
TestClient uses HTTPX. Their versions are pinned, licenses remain their own.
No external research repository is silently cloned or rebranded. Einstein Toolkit
integration is currently a documented CSV boundary for convergence diagnostics,
not a implemented thorn. Model-specific field equations and initial/boundary data
are required before such an integration can become a solver.
