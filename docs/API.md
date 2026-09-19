# Local API and complete experiment inputs

Base: `http://127.0.0.1:8000`. Bearer operator token required under `/api`.
OpenAPI: `/openapi.json`, interactive route documentation: `/docs`.
No automatic outbound requests or notifications are sent by the service.
Content type for JSON mutations is `application/json`. Body maximum: 1 MB.

| Method/path | Result |
|---|---|
| GET /health | Public version and research-mode status |
| GET /api/catalog/models | All M00–M23 with implementation boundaries |
| GET /api/catalog/layers | All L00–L30 with implementation boundaries |
| GET /api/catalog/candidate.schema | M04 JSON Schema |
| GET /api/catalog/capabilities | Available/unavailable capabilities |
| GET /api/experiments | Supported experiment kinds |
| POST /api/runs | Run, persist, return complete experiment record |
| GET /api/runs | Most recent 100 run metadata records |
| GET /api/runs/{id} | Verified input, output and code fingerprint |
| GET /api/runs/{id}/export | ZIP with per-file manifest |
| GET /api/runs/{id}/report | Escaped standalone HTML |
| GET /api/audit | Chain verification and recent events |
| GET /api/controller | Live simulation state and most recent 500 frames |
| POST /api/controller | State command/setpoint |
| POST /api/controller/fault | Inject a named simulated fault |
| POST /api/controller/snapshot | Persist complete checkpointed session telemetry as a run |
| POST /api/physical/open | Always 409, no output; missing physical actuator |

Run request: `{"kind":"evaluate","parameters":{}}`.
Return fields include id, created_at, input_sha, result_sha, code_sha, inputs,
result and code fingerprint. Runtime timestamps and IDs change, deterministic
numerical results do not. Live controller trajectories depend on actual scheduling.

## Every experiment kind

| Kind | Parameters and defaults | Scope |
|---|---|---|
| evaluate | Candidate JSON; defaults in candidate.schema.json | M04 only |
| geodesic | a=1, start_l=-5, beta=.6, angular_fraction=0, kind=timelike, duration=20, steps=2000 | start_l/duration dimensionless; a in metres; output SI |
| wave | model=M04, points=201, extent=10, duration=6, ell=0, damping=0, cfl=.5, initial=gaussian | a=c=1, reflecting boundaries; M00 also accepted |
| wave_convergence | {} | Exact M00 sine wave, three resolutions |
| quantum | theta=1.1, phi=.7, depolarizing=0 | theta/phi radians, 0≤p≤1 |
| qei | tau0_s required | Flat-field Lorentzian benchmark |
| qei_pulse | rho, half_duration_s, tau0_s required | Exact sampling of assigned rectangular pulse |
| control | duration_s=30, target=.4, fault_at_s=null, fault=stale_sensor | Deterministic second-order analog/PID simulation |
| transmission_line | frequencies required, length_m=1, L_H_m=250e-9, C_F_m=100e-12, R_ohm_m=.1, G_siemens_m=0, reference_ohm=50 | Bounded passive RLGC calculation |
| metrology | csv_text required, calibration_csv=null | Supplied complex S21 data; no provenance beyond input |
| nr_constraints | text required | CSV with resolution_h,H_L2,M_L2; diagnostic only |
| causal_graph | nodes, edges required; edge: from,to,time_s | Strict negative cycles of supplied finite graph |
| worldline | samples required: [[t,x,y,z],...] | Piecewise inertial timelike segments in SI |
| symbolic | model=M04 | M00/M01/M04 exact local tensor calculations |

Invalid parameter names/types return 422. These functions have concrete numerical
range and computation budgets, checked in their modules. They do not accept arbitrary
code strings, topology definitions or research source functions.

For live control use `{"action":"initialize"}`, then `arm`, `start`.
Other actions: `hold`, `close`, `off`, `estop`, `setpoint` with numeric `value`.
Fault body: `{"kind":"stale_sensor"}`; alternatives `causal_negative`,
`guard_boundary`, `provenance`, `clock`, `estop`. There is no remote reset command.
Telemetry is checkpointed in 50-frame batches and flushed on state stops/snapshots.
A crash can lose the current uncommitted batch (up to roughly one simulation second);
the dirty marker prevents automatic restart. Checkpoints are simulated measurements.

## Python clients

```python
from pathlib import Path
import httpx

token = Path('.portal/operator.token').read_text().strip()
with httpx.Client(base_url='http://127.0.0.1:8000',
                  headers={'Authorization': f'Bearer {token}'}, timeout=60) as client:
    response = client.post('/api/runs', json={'kind': 'evaluate', 'parameters': {}})
    response.raise_for_status()
    run = response.json()
    print(run['id'], run['result']['physical_decision'])
    archive = client.get(f"/api/runs/{run['id']}/export")
    archive.raise_for_status()
    Path('run.zip').write_bytes(archive.content)
```

The core Python API is also usable directly without the web server:

```python
from portal_tsinder.service import execute
result = execute('wave_convergence', {})
print(result['orders'])
```

## Anchor protocol

`anchors.py` is a local Python API, not a deployed networking service.
See `examples/anchor_pair.py` for a runnable, authenticated pair. Callers provide
pre-shared keys from their own secret store, signed Anchor packets, a clock and
the accepted sequence cache. Sequence protection persists only within that
registry instance; production cross-restart key/nonce management is not supplied.
Physical-mouth evidence is explicitly rejected. There is no hidden driver/remote
formation call behind a successful lookup.
