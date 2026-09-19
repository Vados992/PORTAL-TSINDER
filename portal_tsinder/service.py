"""Bounded experiment dispatcher used identically by CLI and REST API."""
import json
from pathlib import Path
from .contracts import Candidate
from .evaluation import evaluate
from .numerics import geodesic
from .waves import solve, convergence
from .quantum import teleport, flat_qei, sampled_lorentzian_constant_pulse
from .control import closed_loop_experiment
from .metrology import parse_csv, analyze, transmission_line
from .nr import assess_constraints
from .causality import negative_cycle
from .anchors import integrate_worldline

KINDS = ("evaluate", "geodesic", "wave", "wave_convergence", "quantum", "qei", "qei_pulse",
         "control", "transmission_line", "metrology", "nr_constraints", "causal_graph", "worldline", "symbolic")


def catalog(name):
    if name not in ("models", "layers", "candidate.schema", "capabilities"):
        raise ValueError("unknown catalog")
    return json.loads((Path(__file__).parent/"data"/(name+".json")).read_text())


def execute(kind, parameters):
    if kind not in KINDS or not isinstance(parameters, dict):
        raise ValueError("unknown experiment kind or invalid parameters")
    dispatch = {"evaluate": lambda **p: evaluate(Candidate.from_dict(p)),
                "geodesic": geodesic, "wave": solve, "wave_convergence": convergence,
                "quantum": teleport, "qei": flat_qei, "qei_pulse": sampled_lorentzian_constant_pulse,
                "control": closed_loop_experiment, "transmission_line": transmission_line,
                "metrology": lambda csv_text, calibration_csv=None: analyze(parse_csv(csv_text),
                    parse_csv(calibration_csv) if calibration_csv else None),
                "nr_constraints": assess_constraints, "causal_graph": negative_cycle,
                "worldline": integrate_worldline}
    if kind == "symbolic":
        from .symbolic import derive
        return derive(**parameters)
    try:
        return dispatch[kind](**parameters)
    except TypeError as error:
        raise ValueError(f"invalid parameters for {kind}: {error}") from error


def run_experiment(store, kind, parameters):
    result = execute(kind, parameters)
    return store.save_run(kind, parameters, result)
