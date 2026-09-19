"""Strict, finite SI inputs. Scientific evidence is never a user boolean."""
from dataclasses import asdict, dataclass, fields
from enum import Enum
import hashlib
import json
import math
from pathlib import Path
import re


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    CRITICAL = "CRITICAL"
    UNRESOLVED = "UNRESOLVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


def number(value, name, low=-1e100, high=1e100):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: expected a finite number, not a flag or string")
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name}: expected {low} <= value <= {high}")
    return float(value)


def integer(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{name}: expected integer in [{low}, {high}]")
    return value


def identifier(value, name="identifier"):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", value):
        raise ValueError(f"{name}: invalid identifier")
    return value


def canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def digest(data):
    return hashlib.sha256(canonical(data)).hexdigest()


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    def reject(value):
        raise ValueError(f"non-finite JSON constant: {value}")
    return json.loads(text, parse_constant=reject, object_pairs_hook=pairs)


@dataclass(frozen=True)
class Candidate:
    candidate_id: str = "PFA-M04-R1"
    model_id: str = "M04"
    throat_radius_m: float = 1.0
    cutoff_radius_m: float = 10.0
    speed_fraction_c: float = 0.01
    payload_radius_m: float = 0.1
    payload_separation_m: float = 2.0
    tidal_limit_m_s2: float = 9.80665
    exterior_travel_time_s: float = 1.0
    wormhole_travel_time_s: float = 0.1
    mouth_time_offset_s: float = 0.0
    uncertainty_external_s: float = 0.0
    uncertainty_internal_s: float = 0.0
    uncertainty_offset_s: float = 0.0
    causal_guard_margin_s: float = 0.1

    def __post_init__(self):
        identifier(self.candidate_id, "candidate_id")
        if self.model_id != "M04":
            raise ValueError("Candidate evaluator supports M04 only; see registry for other tools")
        number(self.throat_radius_m, "throat_radius_m", 1e-12, 1e12)
        number(self.cutoff_radius_m, "cutoff_radius_m", self.throat_radius_m, 1e15)
        number(self.speed_fraction_c, "speed_fraction_c", 1e-12, 0.999999999)
        number(self.payload_radius_m, "payload_radius_m", 0, 1e12)
        number(self.payload_separation_m, "payload_separation_m", 0, 1e12)
        number(self.tidal_limit_m_s2, "tidal_limit_m_s2", 1e-15, 1e30)
        for name in ("exterior_travel_time_s", "wormhole_travel_time_s",
                     "uncertainty_external_s", "uncertainty_internal_s",
                     "uncertainty_offset_s", "causal_guard_margin_s"):
            number(getattr(self, name), name, 0, 1e15)
        number(self.mouth_time_offset_s, "mouth_time_offset_s", -1e15, 1e15)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError("candidate must be a JSON object")
        extra = set(data) - {f.name for f in fields(cls)}
        if extra:
            raise ValueError(f"unknown/unsupported fields: {', '.join(sorted(extra))}")
        return cls(**data)

    def to_dict(self):
        return asdict(self)


def code_fingerprint():
    root = Path(__file__).parent
    files = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(root.rglob("*"))
             if p.is_file() and p.suffix in {".py", ".json", ".sql", ".js", ".html", ".css"}}
    return {"sha256": digest(files), "files": files}
