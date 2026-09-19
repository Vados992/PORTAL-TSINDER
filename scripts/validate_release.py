"""Run release checks and save actual results. No scientific PA gate is promoted."""
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import platform
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from portal_tsinder.service import execute
from portal_tsinder.contracts import code_fingerprint

out = ROOT/"docs/validation"
out.mkdir(parents=True, exist_ok=True)
suite = unittest.defaultTestLoader.discover(str(ROOT/"tests"))
log = io.StringIO()
result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
(out/"unittest.log").write_text(log.getvalue(), encoding="utf-8")
wave = execute("wave", {})
geo = execute("geodesic", {})
control = execute("control", {})
summary = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "python": platform.python_version(), "platform": platform.system(),
    "tests": {"run": result.testsRun, "failures": len(result.failures),
              "errors": len(result.errors), "skipped": len(result.skipped),
              "passed": result.wasSuccessful()},
    "package_fingerprint": code_fingerprint()["sha256"],
    "metrics": {"geodesic_norm_error": geo["normalization_max_error"],
                "wave_relative_energy_drift": wave["relative_energy_drift"],
                "wave_convergence": execute("wave_convergence", {}),
                "pid_final_setpoint_error": control["absolute_setpoint_error"],
                "teleportation_fidelity": execute("quantum", {})["mean_fidelity"]},
    "physical_aperture": "NOT_IMPLEMENTED",
    "independent_replication": "NOT_PERFORMED",
}
(out/"results.json").write_text(json.dumps(summary, indent=2)+"\n")
print(json.dumps(summary, indent=2))
raise SystemExit(0 if result.wasSuccessful() else 1)
