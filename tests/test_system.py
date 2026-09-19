import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from portal_tsinder.anchors import Anchor, AnchorRegistry, sign, integrate_worldline
from portal_tsinder.control import Controller, State, closed_loop_experiment
from portal_tsinder.contracts import canonical
from portal_tsinder.locking import ServiceLock
from portal_tsinder.metrology import transmission_line, analyze, parse_csv
from portal_tsinder.nr import assess_constraints
from portal_tsinder.service import run_experiment, catalog
from portal_tsinder.storage import Store, verify_bundle


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/"runs.sqlite")

    def test_full_run_export_and_hashes(self):
        run=run_experiment(self.store,"evaluate",{})
        self.assertEqual(hashlib.sha256(canonical(run["result"])).hexdigest(),run["result_sha"])
        self.assertTrue(verify_bundle(self.store.export(run["id"])))
        self.assertEqual(self.store.verify()["status"],"PASS")

    def test_repeat_has_identical_result_hash(self):
        a=run_experiment(self.store,"quantum",{})
        b=run_experiment(self.store,"quantum",{})
        self.assertEqual(a["result_sha"],b["result_sha"])
        self.assertNotEqual(a["id"],b["id"])

    def test_append_only_and_corruption_detection(self):
        self.store.event("TEST",{"data":1})
        with self.store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError): db.execute("UPDATE events SET kind='BAD'")
            db.execute("DROP TRIGGER immutable_events_update")
            db.execute("UPDATE events SET kind='BAD'")
            db.commit()
        self.assertEqual(self.store.verify()["status"],"FAIL")

    def test_retained_head_detects_history_change(self):
        head=self.store.event("ONE",{})
        self.assertEqual(self.store.verify(head)["status"],"PASS")
        self.store.event("TWO",{})
        self.assertEqual(self.store.verify(head)["status"],"FAIL")

    def test_service_lock_excludes_offline_reset(self):
        path=Path(self.tmp.name)/"service.lock"
        with ServiceLock(path):
            with self.assertRaises(RuntimeError):
                with ServiceLock(path): pass

    def test_lockout_persists(self):
        c=Controller(self.store)
        c.command("estop")
        d=Controller(Store(self.store.path))
        self.assertEqual(d.state,State.LOCKOUT)
        with self.assertRaises(ValueError): d.command("off")

    def test_live_telemetry_checkpoint_and_export(self):
        c=Controller(self.store)
        for action in ("initialize","arm","start"): c.command(action)
        for _ in range(75): c.advance()
        c.command("estop")
        run=c.save_snapshot()
        self.assertEqual(len(run["result"]["trace"]),75)
        self.assertTrue(verify_bundle(self.store.export(run["id"])))
        self.assertEqual(self.store.verify()["status"],"PASS")


class ControlTests(unittest.TestCase):
    def running(self):
        c=Controller()
        for action in ("initialize","arm","start"): c.command(action)
        return c

    def test_closed_loop_settles(self):
        result=closed_loop_experiment()
        self.assertLess(result["absolute_setpoint_error"],.002)
        self.assertTrue(all(abs(r["drive"])<=1 for r in result["trace"]))
        self.assertFalse(result["final"]["physical_output_available"])

    def test_interlock_precedes_drive(self):
        c=self.running();c.fault("causal_negative");c.advance()
        self.assertEqual(c.state,State.LOCKOUT)
        self.assertEqual(c.u,0)

    def test_stale_sensor_watchdog(self):
        c=self.running();c.fault("stale_sensor")
        for _ in range(14): c.advance()
        self.assertEqual(c.state,State.LOCKOUT)
        self.assertEqual(c.u,0)

    def test_guard_boundary_closes(self):
        c=self.running();c.fault("guard_boundary");c.advance()
        self.assertNotEqual(c.state,State.RUN)
        self.assertEqual(c.u,0)

    def test_invalid_transition_and_nonfinite_setpoint(self):
        with self.assertRaises(ValueError): Controller().command("start")
        with self.assertRaises(ValueError): self.running().command("setpoint",float("nan"))

    def test_estop_cannot_be_overridden(self):
        c=self.running();c.command("estop")
        for action in ("initialize","arm","start","off","setpoint"):
            with self.subTest(action=action), self.assertRaises(ValueError): c.command(action,.5)

    def test_shutdown_disables_output(self):
        c=self.running();c.advance();c.shutdown()
        self.assertEqual(c.u,0)
        self.assertEqual(c.state,State.OFF)


class AnchorTests(unittest.TestCase):
    def setUp(self):
        self.keys={"A":b"a"*32,"B":b"b"*32}
        self.registry=AnchorRegistry(self.keys)

    def packet(self,name="A",sequence=1,topology="T1"):
        return sign(Anchor(name,topology,"LAB",100,200,sequence,1,(0,0,0)),self.keys[name])

    def test_signed_pair_and_replay(self):
        for name in ("A","B"): self.registry.accept(self.packet(name),101)
        self.assertFalse(self.registry.route("A","B",102)["physical_mouths_verified"])
        with self.assertRaises(ValueError): self.registry.accept(self.packet(),102)

    def test_tamper_expiry_unknown_endpoint(self):
        packet=self.packet();packet["anchor"]["proper_clock_s"]=200
        with self.assertRaises(ValueError): self.registry.accept(packet,102)
        with self.assertRaises(ValueError): self.registry.accept(self.packet(),201)
        with self.assertRaises(ValueError): self.registry.route("A","B",101)

    def test_topology_mismatch(self):
        self.registry.accept(self.packet("A"),101)
        self.registry.accept(self.packet("B",topology="T2"),101)
        with self.assertRaises(ValueError): self.registry.route("A","B",102)

    def test_worldline_time_dilation(self):
        from portal_tsinder.physics import C
        r=integrate_worldline([[0,0,0,0],[10,6*C,0,0]])
        self.assertAlmostEqual(r["clock_offset_s"],2)
        with self.assertRaises(ValueError): integrate_worldline([[0,0,0,0],[1,2*C,0,0]])


class MetrologyTests(unittest.TestCase):
    def test_lossless_matched_line(self):
        r=transmission_line([i*1e6 for i in range(1,101)],R_ohm_m=0)
        self.assertAlmostEqual(r["mean_group_delay_s"],5e-9,places=18)
        for sample in r["samples"]: self.assertAlmostEqual(sample["amplitude"],1,places=12)

    def test_calibration_removes_line(self):
        line=transmission_line([i*1e6 for i in range(1,20)])["samples"]
        r=analyze(line,line)
        self.assertAlmostEqual(r["mean_group_delay_s"],0)
        self.assertTrue(all(abs(p["gain_db"])<1e-10 for p in r["samples"]))

    def test_invalid_phase_and_nonmonotonic_trace(self):
        with self.assertRaises(ValueError): analyze([{"frequency_hz":1,"s21_real":0,"s21_imag":0}]*2)
        with self.assertRaises(ValueError): transmission_line([2,1])
        with self.assertRaises(ValueError): parse_csv("a,b\n1,2")

    def test_nr_convergence_not_physical_gate(self):
        r=assess_constraints("resolution_h,H_L2,M_L2\n.1,.01,.02\n.05,.0025,.005\n.025,.000625,.00125\n")
        self.assertTrue(r["decreasing"])
        self.assertEqual(r["physical_gate_status"],"UNRESOLVED")
        self.assertAlmostEqual(r["orders"][0]["H_L2"],2)

    def test_catalog_complete_and_truthful(self):
        self.assertEqual(len(catalog("models")),24)
        self.assertEqual(len(catalog("layers")),31)
        self.assertEqual(next(m for m in catalog("models") if m["id"]=="M08")["implementation"],"CATALOG_ONLY")


class NativeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("g++"),"C++ compiler not available")
    def test_cpp_guard_and_invalid_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=str(Path(tmp)/"guard")
            root=Path(__file__).resolve().parents[1]
            subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror",str(root/"native/guard.cpp"),"-o",target],check=True,capture_output=True)
            cases="1 .1 0 0 0 0 .1\n1 .1 1 0 0 0 .1\n1 .1 2 0 0 0 .1\nnan 1 0 0 0 0 0\n"
            r=subprocess.run([target],input=cases,text=True,capture_output=True,check=True)
            self.assertEqual([json.loads(s)["action"] for s in r.stdout.splitlines()],
                             ["ALLOW_ANALOG","CLOSE","LOCKOUT","LOCKOUT"])
