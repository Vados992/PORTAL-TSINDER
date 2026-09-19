"""Executable analog SIMULATION controller with a latched veto state machine.

The plant is x''+2*zeta*omega*x'+omega^2*x=omega^2*u, dimensionless.
No output is ever connected to hardware. Python threads and the optional C++
diagnostic are not certified safety PLCs or hard real-time control paths.
"""
from collections import deque
from enum import Enum
import math
import threading
import time
import uuid
from .contracts import number
from .causality import route_guard
from .numerics import rk4


class State(str, Enum):
    OFF = "OFF"
    SAFE = "SAFE"
    ARMED = "ARMED_ANALOG"
    RUN = "RUN_ANALOG"
    HOLD = "HOLD"
    CLOSE = "CLOSE"
    LOCKOUT = "LOCKOUT"


class PID:
    def __init__(self, kp=1.8, ki=1.5, kd=0.5, limit=1.0):
        self.kp, self.ki, self.kd, self.limit = kp, ki, kd, limit
        self.integral = 0.0

    def update(self, target, measured, velocity, dt):
        error = target-measured
        proposed = self.integral+dt*error
        raw = self.kp*error+self.ki*proposed-self.kd*velocity
        out = max(-self.limit, min(self.limit, raw))
        if raw == out or error*raw < 0:
            self.integral = proposed
        return out


class Controller:
    def __init__(self, store=None):
        self.store = store
        locked = store.get_state("lockout", False) if store else False
        self.state = State.LOCKOUT if locked else State.OFF
        self.reason = "Persisted lockout" if locked else "Ready for self-test"
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.thread = None
        self.pid = PID()
        self.x = self.v = self.u = self.t = 0.0
        self.target = 0.4
        self.offset = 0.0
        self.sensor_age = 0.0
        self.sensor_lost = False
        self.trace = deque(maxlen=2000)
        self.audit_age = 0.0
        self.session_id = uuid.uuid4().hex if store else "deterministic-simulation"
        self.segment = 0
        self.pending_frames = []
        if store and store.verify()["status"] != "PASS":
            self._transition(State.LOCKOUT, "Provenance integrity failure")

    def _transition(self, new, reason):
        old = self.state
        self.state, self.reason = new, reason
        if new != State.RUN:
            self.u = 0.0
        if new == State.LOCKOUT and self.store:
            self.store.set_state("lockout", True, "LOCKOUT_LATCHED")
        if self.store and (old != new or new == State.LOCKOUT):
            self.store.event("CONTROL_TRANSITION", {"from": old.value, "to": new.value, "reason": reason})
            if new in (State.LOCKOUT, State.OFF, State.HOLD):
                self.flush_telemetry()

    def flush_telemetry(self):
        if self.store and self.pending_frames:
            self.store.append_telemetry(self.session_id, self.segment, self.pending_frames)
            self.segment += 1
            self.pending_frames = []

    def save_snapshot(self):
        with self.lock:
            if self.store is None:
                raise ValueError("controller storage unavailable")
            self.flush_telemetry()
            return self.store.save_run("live_control", {"session_id": self.session_id},
                {"scope": "LIVE_ANALOG_SIMULATION", "snapshot": self.snapshot(),
                 "trace": self.store.telemetry(self.session_id), "spacetime_stability": "UNRESOLVED"})

    def command(self, action, value=None):
        with self.lock:
            if action == "estop":
                self._transition(State.LOCKOUT, "Operator emergency stop (simulation)")
            elif self.state == State.LOCKOUT:
                raise ValueError("LOCKOUT: offline independent review and reset required; UI cannot override")
            elif action == "initialize" and self.state == State.OFF:
                self._transition(State.SAFE, "Software self-test completed; simulated sensors available")
            elif action == "arm" and self.state == State.SAFE:
                if self.sensor_lost or self.sensor_age > 0.25:
                    raise ValueError("sensor validity required")
                self._transition(State.ARMED, "Simulation contract active")
            elif action == "start" and self.state == State.ARMED:
                self.pid = PID()
                self._transition(State.RUN, "Simulated analog run started")
            elif action == "hold" and self.state == State.RUN:
                self._transition(State.HOLD, "Operator hold; drive disabled")
            elif action == "close" and self.state in (State.RUN, State.ARMED, State.HOLD):
                self._transition(State.CLOSE, "Drive disabled; passive simulated decay")
            elif action == "off":
                self._transition(State.OFF, "Software output disabled")
            elif action == "setpoint" and self.state in (State.SAFE, State.ARMED, State.RUN):
                self.target = number(value, "setpoint", -0.8, 0.8)
                if self.store:
                    self.store.event("SETPOINT", {"value": self.target, "scope": "SIMULATED"})
            else:
                raise ValueError(f"command {action} invalid in {self.state.value}")
            return self.snapshot()

    def fault(self, kind):
        with self.lock:
            if kind == "stale_sensor":
                self.sensor_lost = True
            elif kind == "causal_negative":
                self.offset = 2.0
            elif kind == "guard_boundary":
                self.offset = 1.0
            elif kind in ("provenance", "clock", "estop"):
                self._transition(State.LOCKOUT, f"Injected {kind} fault in simulation")
            else:
                raise ValueError("unknown simulated fault")
            return self.snapshot()

    def advance(self, dt=0.02):
        number(dt, "dt", 1e-6, 0.1)
        with self.lock:
            prior_state = self.state
            self.t += dt
            self.sensor_age = self.sensor_age+dt if self.sensor_lost else 0.0
            guard = route_guard(1.0, 0.1, self.offset, policy=0.1)
            if self.state not in (State.OFF, State.LOCKOUT):
                if guard["status"] == "FAIL":
                    self._transition(State.LOCKOUT, "Negative reduced causal margin")
                elif self.sensor_age > 0.25:
                    self._transition(State.LOCKOUT, "Stale sensor watchdog")
                elif guard["safe_margin_s"] <= 1e-12 and self.state in (State.RUN, State.ARMED):
                    self._transition(State.CLOSE, "Reduced causal margin exhausted")
            self.u = self.pid.update(self.target, self.x, self.v, dt) if self.state == State.RUN else 0.0
            def rhs(t, y):
                return [y[1], 4*(self.u-y[0])-1.6*y[1]]
            self.x, self.v = rk4(rhs, self.t, [self.x, self.v], dt)
            if abs(self.x) > 2 or abs(self.v) > 10:
                self._transition(State.LOCKOUT, "Simulated plant envelope exceeded")
            if self.state == State.CLOSE and abs(self.x) < 0.01 and abs(self.v) < 0.01:
                self._transition(State.SAFE, "Simulated plant decayed to safe envelope")
            self.trace.append({"t_s": self.t, "x": self.x, "v": self.v, "u": self.u,
                               "target": self.target, "state": self.state.value})
            if prior_state not in (State.OFF, State.SAFE, State.LOCKOUT) or self.state == State.RUN:
                self.pending_frames.append(dict(self.trace[-1]))
                if len(self.pending_frames) >= 50 or self.state == State.LOCKOUT:
                    self.flush_telemetry()
            return self.snapshot()

    def snapshot(self):
        with self.lock:
            return {"mode": "SIMULATION_ONLY", "session_id": self.session_id, "state": self.state.value, "reason": self.reason,
                    "time_s": self.t, "position": self.x, "velocity": self.v, "drive": self.u,
                    "setpoint": self.target, "sensor_age_s": self.sensor_age,
                    "guard": route_guard(1, 0.1, self.offset, policy=0.1),
                    "physical_output_available": False, "trace": list(self.trace)[-500:]}

    def _loop(self):
        previous = time.monotonic()
        while not self.stop_event.wait(0.02):
            current = time.monotonic()
            elapsed, previous = current-previous, current
            try:
                if elapsed > 0.25:
                    with self.lock:
                        if self.state in (State.RUN, State.ARMED):
                            self._transition(State.LOCKOUT, "Controller scheduling watchdog")
                self.advance(min(elapsed, 0.1))
                self.audit_age += elapsed
                if self.store and self.audit_age >= 5:
                    self.audit_age = 0
                    if self.store.verify()["status"] != "PASS":
                        with self.lock:
                            self._transition(State.LOCKOUT, "Audit verification failed")
            except Exception:
                # Local veto does not depend on storage being writable.
                with self.lock:
                    self.state, self.u = State.LOCKOUT, 0.0
                    self.reason = "Controller/storage exception; drive disabled"
                if self.store:
                    try:
                        self.store.set_state("lockout", True, "CONTROLLER_EXCEPTION")
                    except Exception:
                        pass

    def start_background(self):
        if self.thread is not None:
            raise RuntimeError("controller already started")
        self.thread = threading.Thread(target=self._loop, name="analog-simulation-veto", daemon=True)
        self.thread.start()

    def shutdown(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)
        with self.lock:
            self.u = 0.0
            if self.state != State.LOCKOUT:
                self._transition(State.OFF, "Service shutdown; simulated drive disabled")
            self.flush_telemetry()


def closed_loop_experiment(duration_s=30.0, target=0.4, fault_at_s=None, fault="stale_sensor"):
    number(duration_s, "duration_s", 0.1, 120)
    if fault_at_s is not None:
        number(fault_at_s, "fault_at_s", 0, duration_s)
    controller = Controller()
    for action in ("initialize", "arm", "start"):
        controller.command(action)
    controller.command("setpoint", target)
    injected = False
    trace = []
    for _ in range(math.ceil(duration_s/0.02)):
        if fault_at_s is not None and controller.t >= fault_at_s and not injected:
            controller.fault(fault)
            injected = True
        snap = controller.advance(0.02)
        trace.append({key: snap[key] for key in ("time_s", "position", "drive", "state")})
    return {"scope": "SECOND_ORDER_ANALOG_SIMULATION", "final": controller.snapshot(),
            "absolute_setpoint_error": abs(controller.x-target), "trace": trace,
            "spacetime_stability": "UNRESOLVED"}
