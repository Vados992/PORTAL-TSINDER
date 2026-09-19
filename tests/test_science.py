import math
import unittest
from portal_tsinder.contracts import Candidate, strict_json
from portal_tsinder import physics as p
from portal_tsinder.evaluation import evaluate
from portal_tsinder.causality import route_guard, covariance_bound, clock_offset, negative_cycle
from portal_tsinder.numerics import simpson, geodesic
from portal_tsinder.quantum import teleport, flat_qei
from portal_tsinder.waves import solve, convergence
from portal_tsinder.symbolic import derive


class PhysicsTests(unittest.TestCase):
    def test_document_regression(self):
        self.assertAlmostEqual(p.stress(1, 1)["radial_NEC_J_m3"]/-9.630907773444846e42, 1, places=13)
        self.assertAlmostEqual(p.volume_energy_limit(1)/-1.901065e44, 1, places=6)
        self.assertAlmostEqual(p.proper_distance(10, 1)*2, 19.899748742, places=8)

    def test_volume_integral_independent_quadrature(self):
        for a in (0.01, 1, 100):
            length = p.proper_distance(10*a, a)
            numeric = simpson(lambda l: p.stress(math.hypot(l, a), a)["rho_J_m3"]*
                              4*math.pi*(l*l+a*a), -length, length, 10000)
            self.assertAlmostEqual(numeric/p.volume_energy(10*a, a), 1, places=10)

    def test_scaling_and_energy_conditions(self):
        self.assertAlmostEqual(p.stress(2, 2)["rho_J_m3"]/p.stress(1, 1)["rho_J_m3"], .25)
        self.assertEqual(p.stress(3, 1)["tangential_NEC_J_m3"], 0)
        self.assertGreater(p.invariants(0, 1)["kretschmann_m4"], 0)

    def test_payload_tidal_speed_dependence(self):
        self.assertEqual(p.radial_traveler_tides(0, 1, 0, 2)["transverse_m_s2"], 0)
        self.assertAlmostEqual(p.radial_traveler_tides(0, 1, .6, 2)["transverse_curvature_m2"], .5625)
        self.assertGreater(p.radial_traveler_tides(0, 1, .01, 2)["transverse_m_s2"], 1e10)

    def test_formal_ghost_constraints(self):
        for l in (-10, -1, 0, .7, 10):
            result=p.phantom_source(l, 1)
            self.assertAlmostEqual(result["klein_gordon_residual_m2"], 0, places=13)
            self.assertAlmostEqual(result["ADM_Hamiltonian_residual_m2"], 0, places=13)
            self.assertTrue(result["negative_kinetic_energy"])

    def test_schwarzschild_is_not_traversable_bridge(self):
        mass=1e30
        rs=2*p.G*mass/p.C**2
        self.assertFalse(p.schwarzschild(rs, mass)["exterior_chart_valid"])
        self.assertEqual(p.schwarzschild(2*rs, mass)["bridge_traversability"], "FAIL")

    def test_strict_finite_and_no_boolean_promotion(self):
        for val in (True, "1", float("nan"), float("inf"), 0, -1):
            with self.subTest(val=val), self.assertRaises(ValueError):
                Candidate(throat_radius_m=val)
        for field in ("source_lagrangian_declared", "global_causality_certified", "physical_aperture_authorized"):
            with self.assertRaises(ValueError):
                Candidate.from_dict({field:True})

    def test_no_unknown_model_or_duplicate_keys(self):
        with self.assertRaises(ValueError): Candidate(model_id="M08")
        with self.assertRaises(ValueError): strict_json('{"x":1,"x":2}')
        with self.assertRaises(ValueError): strict_json('{"x":NaN}')

    def test_claim_vector_never_promotes_physics(self):
        r=evaluate()
        self.assertEqual(r["highest_claim"], "FORMAL_TRAVERSABILITY")
        self.assertFalse(r["physical_aperture_authorized"])
        self.assertTrue(all(g["status"]=="UNRESOLVED" for g in r["physical_gates"]))
        self.assertEqual(r["gates"][3]["status"], "FAIL")
        self.assertEqual(evaluate({"payload_radius_m":1})["gates"][11]["status"],"FAIL")

    def test_symbolic_derivation_all_supported_models(self):
        for model in ("M00", "M01", "M04"):
            with self.subTest(model=model):
                self.assertEqual(derive(model)["status"], "PASS")
                self.assertTrue(derive(model)["checks"]["contracted_Bianchi"])


class CausalityTests(unittest.TestCase):
    def test_guard_equal_boundary_closes(self):
        self.assertEqual(route_guard(1,.1,1,policy=.1)["action"], "CLOSE")
        self.assertEqual(route_guard(1,.1,2)["action"], "LOCKOUT")
        self.assertEqual(route_guard(1,.1,0,policy=.1)["status"], "PASS")

    def test_uncertainty_exhausts_guard(self):
        self.assertEqual(route_guard(1,.1,0,u_external=1.2)["action"], "CLOSE")

    def test_covariance_and_invalid_correlations(self):
        self.assertAlmostEqual(covariance_bound([[1,0,0],[0,4,0],[0,0,9]])["bound_s"],18)
        with self.assertRaises(ValueError): covariance_bound([[1,2,0],[2,1,0],[0,0,1]])
        with self.assertRaises(ValueError): covariance_bound([[1e-30,2e-30,0],[2e-30,1e-30,0],[0,0,1e-30]])

    def test_clock_small_velocity_and_relativistic(self):
        self.assertGreater(clock_offset(1,1e-3), 0)
        self.assertAlmostEqual(clock_offset(10,.6*p.C), 2)

    def test_negative_cycle_witness(self):
        result=negative_cycle(["A","B"],[{"from":"A","to":"B","time_s":-2},{"from":"B","to":"A","time_s":1}])
        self.assertEqual(result["total_time_s"], -1)
        self.assertEqual(len(result["negative_cycle"]), 2)

    def test_no_cycle_not_global_certificate(self):
        result=negative_cycle(["A","B"],[{"from":"A","to":"B","time_s":1}])
        self.assertEqual(result["status"], "UNRESOLVED")
        self.assertFalse(result["global_certificate"])


class NumericTests(unittest.TestCase):
    def test_radial_geodesic_exact_solution(self):
        r=geodesic(beta=.6,start_l=-5,duration=20)
        self.assertAlmostEqual(r["path"][-1]["l_m"], 10, places=10)
        self.assertLess(r["normalization_max_error"],1e-10)
        self.assertTrue(r["crossed_throat"])

    def test_null_geodesic(self):
        r=geodesic(kind="null",start_l=-5,duration=10)
        self.assertAlmostEqual(r["path"][-1]["l_m"],5,places=10)
        self.assertAlmostEqual(r["path"][-1]["coordinate_time_s"]*p.C,10,places=10)

    def test_angular_momentum_barrier(self):
        r=geodesic(kind="null",angular_fraction=.8)
        self.assertFalse(r["crossed_throat"])
        self.assertLess(r["normalization_max_error"],1e-6)

    def test_bad_step_rejected(self):
        with self.assertRaises(ValueError): geodesic(beta=.999,duration=100,steps=10)

    def test_wave_second_order_convergence(self):
        r=convergence()
        self.assertEqual(r["status"],"PASS")
        self.assertTrue(all(1.8<p<2.2 for p in r["orders"]))

    def test_wave_discrete_energy(self):
        r=solve()
        self.assertLess(abs(r["relative_energy_drift"]),1e-9)
        self.assertEqual(r["nonlinear_spacetime_stability"],"UNRESOLVED")

    def test_wave_damping_and_compute_limit(self):
        self.assertLess(solve(damping=.2)["relative_energy_drift"],0)
        with self.assertRaises(ValueError): solve(points=501,extent=2,duration=30,cfl=.05)


class QuantumTests(unittest.TestCase):
    def test_all_measurement_branches_and_no_signaling(self):
        for theta in (0,.4,1.5,math.pi):
            r=teleport(theta=theta)
            self.assertAlmostEqual(r["mean_fidelity"],1)
            for branch in r["branches"]:
                self.assertAlmostEqual(branch["probability"],.25)
                self.assertAlmostEqual(branch["corrected_fidelity"],1)
            density=r["bob_before_classical_message"]
            self.assertAlmostEqual(density[0][0][0],.5)
            self.assertAlmostEqual(density[1][1][0],.5)
            self.assertAlmostEqual(abs(complex(*density[0][1])),0)

    def test_depolarization(self):
        self.assertAlmostEqual(teleport(depolarizing=1)["mean_fidelity"],.5)

    def test_qei_dimensions_and_scope(self):
        self.assertAlmostEqual(flat_qei(1)["lower_bound_J_m3"]/-3.717796e-62,1,places=6)
        self.assertAlmostEqual(flat_qei(.5)["lower_bound_J_m3"]/flat_qei(1)["lower_bound_J_m3"],16)
        self.assertEqual(flat_qei(1)["wormhole_applicability"],"UNRESOLVED")
