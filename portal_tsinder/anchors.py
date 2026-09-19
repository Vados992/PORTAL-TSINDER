"""Paired simulated/signal anchors authenticated using pre-shared HMAC keys.

This is a symmetric software authentication protocol, not physical existence
evidence, not asymmetric signatures, and not a network time synchronization system.
"""
from dataclasses import dataclass, asdict
import hashlib
import hmac
from .contracts import canonical, identifier, number, integer
from .physics import C


@dataclass(frozen=True)
class Anchor:
    endpoint_id: str
    topology_id: str
    frame_id: str
    issued_at_s: float
    expires_at_s: float
    sequence: int
    proper_clock_s: float
    position_m: tuple
    evidence_class: str = "SIMULATED"

    def __post_init__(self):
        for field in ("endpoint_id", "topology_id", "frame_id"):
            identifier(getattr(self, field), field)
        number(self.issued_at_s, "issued_at_s", 0, 1e15)
        number(self.expires_at_s, "expires_at_s", self.issued_at_s, self.issued_at_s+300)
        if self.expires_at_s <= self.issued_at_s:
            raise ValueError("anchor validity interval must have positive duration")
        integer(self.sequence, "sequence", 0, 2**53-1)
        number(self.proper_clock_s, "proper_clock_s", 0, 1e15)
        if len(self.position_m) != 3:
            raise ValueError("three position coordinates required")
        for v in self.position_m:
            number(v, "position", -1e15, 1e15)
        if self.evidence_class not in ("SIMULATED", "SIGNAL_PORT"):
            raise ValueError("physical mouth evidence is not supported")


def sign(anchor, key):
    if len(key) < 32:
        raise ValueError("HMAC key must be at least 32 bytes")
    body = asdict(anchor)
    return {"anchor": body, "hmac_sha256": hmac.new(key, canonical(body), hashlib.sha256).hexdigest()}


class AnchorRegistry:
    def __init__(self, keys):
        self.keys, self.anchors = dict(keys), {}

    def accept(self, packet, now_s):
        number(now_s, "now_s", 0, 1e15)
        if set(packet) != {"anchor", "hmac_sha256"}:
            raise ValueError("invalid anchor packet")
        anchor = Anchor(**packet["anchor"])
        key = self.keys.get(anchor.endpoint_id)
        if key is None:
            raise ValueError("unknown anchor key")
        expected = sign(anchor, key)["hmac_sha256"]
        if not isinstance(packet["hmac_sha256"], str) or not hmac.compare_digest(expected, packet["hmac_sha256"]):
            raise ValueError("anchor authentication failure")
        if not anchor.issued_at_s <= now_s < anchor.expires_at_s:
            raise ValueError("anchor stale or from future")
        old = self.anchors.get(anchor.endpoint_id)
        if old and anchor.sequence <= old.sequence:
            raise ValueError("replayed anchor sequence")
        self.anchors[anchor.endpoint_id] = anchor
        return anchor

    def route(self, endpoint_a, endpoint_b, now_s):
        if endpoint_a == endpoint_b:
            raise ValueError("two distinct anchors required")
        try:
            a, b = self.anchors[endpoint_a], self.anchors[endpoint_b]
        except KeyError as error:
            raise ValueError("ENDPOINT_MISSING") from error
        if a.topology_id != b.topology_id or a.frame_id != b.frame_id:
            raise ValueError("topology/frame mismatch")
        if any(not x.issued_at_s <= now_s < x.expires_at_s for x in (a, b)):
            raise ValueError("stale route")
        return {"A": asdict(a), "B": asdict(b), "physical_mouths_verified": False}


def integrate_worldline(samples):
    """Piecewise constant segment speeds in one inertial frame; SI clock integral."""
    from math import sqrt
    if not 2 <= len(samples) <= 10000:
        raise ValueError("2..10000 worldline samples required")
    clean = []
    for row in samples:
        if len(row) != 4:
            raise ValueError("worldline row is [t_s,x_m,y_m,z_m]")
        clean.append([number(v, "worldline value", -1e15, 1e15) for v in row])
    proper, elapsed, rows = 0.0, 0.0, []
    for left, right in zip(clean, clean[1:]):
        dt = right[0]-left[0]
        if dt <= 0:
            raise ValueError("worldline timestamps must increase")
        beta2 = sum(((b-a)/(dt*C))**2 for a, b in zip(left[1:], right[1:]))
        if beta2 >= 1:
            raise ValueError("endpoint segment is not timelike")
        proper += dt*sqrt(1-beta2)
        elapsed += dt
        rows.append({"lab_s": elapsed, "proper_s": proper, "beta": sqrt(beta2)})
    return {"proper_elapsed_s": proper, "lab_elapsed_s": elapsed,
            "clock_offset_s": elapsed-proper, "segments": rows,
            "scope": "PIECEWISE_INERTIAL_KINEMATICS", "acceleration_phases": "NOT_MODELED"}
