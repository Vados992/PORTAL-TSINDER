# Release 0.1.0 validation

Performed 2026-09-19 in Linux, Python 3.12.14. Actual machine results are in
[validation/results.json](validation/results.json); the full test transcript is
[validation/unittest.log](validation/unittest.log).

## Executed

| Check | Observed result |
|---|---|
| Unit and integration suite | **59 run, 0 failures, 0 errors, 0 skipped** |
| M04 document numerical regression | PASS |
| Separate proper-volume quadrature | PASS |
| SymPy M00/M01/M04 derivation, Riemann contraction, Bianchi, Kretschmann | PASS |
| Radial/null/angular geodesic controls | PASS |
| Wave analytic refinement | Orders 2.00002085 and 2.00000522 |
| Default undamped wave staggered energy drift | −1.4051e−15 relative |
| Default 30-s PID simulation | Final absolute setpoint error 4.4845e−10 |
| Quantum teleportation | Weighted fidelity 0.9999999999999998; all four branches tested |
| HMAC tamper/replay/expiry/topology checks | PASS |
| C++17 guard compiled and executed | PASS; positive, zero-boundary, negative and invalid-input controls |
| Controller lockout and telemetry persistence | PASS |
| API authentication, finite JSON, CSRF/origin, host, exports | PASS via real FastAPI TestClient |
| Clean virtual environment dependency install and wheel build/install | PASS |
| Installed package run outside source directory | Six demo experiments completed; audit PASS |
| Frontend and browser-test JavaScript syntax | PASS (`node --check`) |
| GitHub Actions Python 3.11 / 3.12 / 3.13 | PASS: test suite, demo and audit on all three versions |
| GitHub Actions Chromium end-to-end | PASS: `node scripts/browser-smoke.cjs` |

Remote results were verified from the completed jobs of
[GitHub Actions run 35455905840](https://github.com/Vados992/PORTAL-TSINDER/actions/runs/35455905840)
for commit `f2e7700f114cdfde942ff096c4233ea790c999ab` on 2026-09-19.
All four jobs completed successfully. The following documentation/license update
does not change the scientific, service, frontend or test code validated by that run.

The exact-zero radial geodesic normalization error is an outcome of this simple
constant-velocity benchmark, not a universal accuracy guarantee. The angular test
also checks invariant drift. PID values apply to the explicitly specified ordinary
second-order plant, not to spacetime geometry.

## Not executed / limitations

- **Local browser execution: unavailable.** The build environment would not
  execute its Chromium binary (`EACCES`), and its supported cloud browser rejected
  the local service address (`ERR_BLOCKED_BY_CLIENT`). The same end-to-end test
  subsequently passed on GitHub Actions. Manual visual review was not performed.
- **Docker image/Compose: NOT EXECUTED.** Docker is unavailable in the build
  environment; recipes are supplied, not represented as a tested deployment.
- **Windows/macOS: NOT EXECUTED.** Python 3.11/3.13 were tested on Linux in
  GitHub Actions, not in the local build environment.
- **No hardware, physical aperture, nonlinear numerical relativity, independent
  laboratory, second CAS or independent-team replication was tested.**
- The full 24-model catalog does not have 24 implemented solvers. See traceability.
- A 59-test suite provides bounded evidence; it is not proof that all possible
  parameters, deployments or future modifications behave correctly.

## Repeat

```bash
python scripts/validate_release.py
python -m portal_tsinder demo
python -m portal_tsinder verify
node --check portal_tsinder/web/app.js
```

For a browser-capable machine, install `playwright@1.62.1`, install its Chromium,
then `node scripts/browser-smoke.cjs`. The test starts a disposable local service,
uses a freshly generated test token, exercises the main views and ZIP export,
and checks mobile overflow. Set `PORTAL_TEST_PYTHON` if Python is not named python3.
`PORTAL_CHROMIUM_EXECUTABLE` may identify an existing approved browser installation.
Do not use this option to bypass an execution restriction.

After any source change, rerun relevant checks and regenerate the release manifest:
`python scripts/release_manifest.py`. The manifest intentionally excludes itself.
The linked GitHub Actions run records the observed remote results; the presence
of a workflow file alone is not evidence of a successful test.
