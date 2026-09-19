import json
from pathlib import Path
import tempfile
import unittest
from fastapi.testclient import TestClient
from portal_tsinder.api import create_app

TOKEN="test-only-operator-token-not-a-deployed-secret-12345"


class APITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app=create_app(self.tmp.name,token_override=TOKEN,background=False)
        self.client=TestClient(self.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__,None,None,None)
        self.headers={"Authorization":f"Bearer {TOKEN}"}

    def post(self,path,data):
        return self.client.post(path,json=data,headers=self.headers)

    def test_health_static_and_authentication(self):
        self.assertEqual(self.client.get("/health").status_code,200)
        self.assertEqual(self.client.get("/").status_code,200)
        self.assertIn("Content-Security-Policy",self.client.get("/").headers)
        self.assertEqual(self.client.get("/api/runs").status_code,401)
        self.assertEqual(self.client.get("/api/runs",headers=self.headers).status_code,200)

    def test_run_report_bundle_end_to_end(self):
        r=self.post("/api/runs",{"kind":"evaluate","parameters":{}})
        self.assertEqual(r.status_code,200,r.text)
        ident=r.json()["id"]
        self.assertEqual(self.client.get(f"/api/runs/{ident}",headers=self.headers).status_code,200)
        report=self.client.get(f"/api/runs/{ident}/report",headers=self.headers)
        self.assertIn("No physical aperture",report.text)
        bundle=self.client.get(f"/api/runs/{ident}/export",headers=self.headers)
        from portal_tsinder.storage import verify_bundle
        self.assertTrue(verify_bundle(bundle.content))

    def test_bad_parameters_and_claim_forgery(self):
        for parameters in ({"global_causality_certified":True},{"throat_radius_m":True},{"speed_fraction_c":1}):
            r=self.post("/api/runs",{"kind":"evaluate","parameters":parameters})
            self.assertEqual(r.status_code,422)

    def test_strict_json_and_body_budget(self):
        headers={**self.headers,"Content-Type":"application/json"}
        for body in ('{"kind":"evaluate","kind":"wave","parameters":{}}','{"kind":"evaluate","parameters":{"throat_radius_m":NaN}}'):
            self.assertEqual(self.client.post("/api/runs",content=body,headers=headers).status_code,422)
        self.assertEqual(self.client.post("/api/runs",content='x'*1_000_001,headers=headers).status_code,413)

    def test_csrf_origin_and_dns_rebinding(self):
        r=self.client.post("/api/controller",json={"action":"initialize"},
                           headers={**self.headers,"Origin":"https://evil.example"})
        self.assertEqual(r.status_code,403)
        self.assertEqual(self.client.get("/health",headers={"Host":"evil.example"}).status_code,400)

    def test_controller_commands_and_lockout(self):
        for action in ("initialize","arm","start","estop"):
            self.assertEqual(self.post("/api/controller",{"action":action}).status_code,200)
        self.assertEqual(self.post("/api/controller",{"action":"start"}).status_code,409)
        self.assertEqual(self.post("/api/controller",{"action":"reset"}).status_code,409)
        self.assertEqual(self.post("/api/physical/open",{}).status_code,409)

    def test_catalog_all_workflows(self):
        self.assertEqual(len(self.client.get("/api/catalog/models",headers=self.headers).json()),24)
        self.assertEqual(self.client.get("/api/catalog/../operator.token",headers=self.headers).status_code,404)
        response=self.post("/api/runs",{"kind":"quantum","parameters":{}})
        self.assertAlmostEqual(response.json()["result"]["mean_fidelity"],1)

    def test_missing_run_and_path_traversal(self):
        self.assertEqual(self.client.get("/api/runs/unknown",headers=self.headers).status_code,404)
        self.assertNotEqual(self.client.get("/assets/../../operator.token").status_code,200)

    def test_dirty_shutdown_blocks_restart(self):
        self.app.state.store.set_state("service_dirty",True,"SIMULATED_DIRTY_EXIT")
        # Test the next application in a separate database, avoiding concurrent service lock.
        with tempfile.TemporaryDirectory() as other:
            from portal_tsinder.storage import Store
            s=Store(Path(other)/"portal.sqlite")
            s.set_state("service_dirty",True,"DIRTY_EXIT")
            with TestClient(create_app(other,token_override=TOKEN,background=False)) as client:
                r=client.get("/api/controller",headers=self.headers)
                self.assertEqual(r.json()["state"],"LOCKOUT")


if __name__=="__main__": unittest.main()
