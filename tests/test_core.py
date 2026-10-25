"""Deterministic tests. LLM behaviour is replaced by explicit test doubles that are never used in
reported experiments (the runner refuses to start LLM conditions without a reachable Ollama model)."""
import unittest

from hmcoop.episode import Episode, central_plan, run_episode
from hmcoop.llm import LLMCall, _check, choice_schema
from hmcoop.model import Mode, Option
from hmcoop.scenarios import EVENTS, HOUSEHOLDS, make_scenario
from hmcoop.world import Conditions, enumerate_options, execute, validate


class ScriptedLLM:
    """Test double: answers every request with a fixed dict (or a failure)."""
    model = "test-double"

    def __init__(self, answer=None, fail=False, pick_first=False):
        self.answer, self.fail, self.pick_first, self.n = answer, fail, pick_first, 0

    def chat(self, purpose, agent, system, user, schema):
        self.n += 1
        if self.fail:
            return LLMCall(purpose, agent, False, None, "garbage", "invalid output: test", 1.0, 10, 2)
        data = dict(self.answer or {})
        if self.pick_first:
            data.setdefault("reason", "first")
            data["option"] = schema["properties"]["option"]["enum"][0]
        return LLMCall(purpose, agent, True, data, str(data), "", 1.0, 10, 2)


def opt(hh, cond, mid, mode, escort=None):
    return next(o for o in enumerate_options(hh, cond, mid) if o.mode == mode and o.escort == escort)


class WorldTests(unittest.TestCase):
    def test_text_only_events_are_invisible_to_the_planner(self):
        hh, ev = make_scenario("martin", "car_breakdown")
        self.assertEqual(Conditions.observed(hh, ev).cars(), 1)
        self.assertEqual(Conditions.truth(hh, ev).cars(), 0)
        hh, ev = make_scenario("martin", "bus_strike")
        self.assertFalse(Conditions.observed(hh, ev).available(hh.member("marie"), Mode.BUS))

    def test_options_respect_capabilities(self):
        hh, ev = make_scenario("martin", "none")
        obs = Conditions.observed(hh, ev)
        self.assertEqual(enumerate_options(hh, obs, "lea"), [Option("O1", "lea", None)])  # cannot go alone
        self.assertFalse(any(o.mode == Mode.CAR for o in enumerate_options(hh, obs, "tom")))
        self.assertFalse(any(o.mode == Mode.BIKE and o.escort for o in enumerate_options(hh, obs, "paul")))
        hh, _ = make_scenario("garcia", "none")
        self.assertFalse(any(o.mode == Mode.CAR for o in enumerate_options(hh, obs.__class__.observed(hh, ev), "david")))

    def test_car_location_is_tracked_and_second_driver_fails(self):
        hh, ev = make_scenario("martin", "none")
        truth = Conditions.truth(hh, ev)
        plan = {"marie": opt(hh, truth, "marie", Mode.CAR), "paul": opt(hh, truth, "paul", Mode.CAR, "lea"),
                "tom": opt(hh, truth, "tom", Mode.BIKE)}
        ex = execute(hh, plan, truth)
        self.assertEqual(ex.failures["car_unavailable"], 1)
        self.assertEqual(ex.car_trips[0]["driver"], "marie")
        self.assertEqual(ex.car_trips[0]["to"], "Purpan")
        self.assertNotEqual(ex.outcomes["paul"].mode, "car")
        self.assertIn("car1 at Purpan", " ".join(ex.log))

    def test_broken_car_and_unaccompanied_child(self):
        hh, ev = make_scenario("martin", "car_breakdown")
        truth, obs = Conditions.truth(hh, ev), Conditions.observed(hh, ev)
        self.assertFalse(any(o.mode == Mode.CAR for o in enumerate_options(hh, truth, "paul")))
        plan = {"marie": opt(hh, obs, "marie", Mode.BUS), "paul": opt(hh, obs, "paul", Mode.CAR),
                "tom": opt(hh, obs, "tom", Mode.BIKE)}
        ex = execute(hh, plan, truth)
        self.assertIn("would not start", " ".join(ex.log))
        self.assertTrue(ex.outcomes["lea"].missed)
        self.assertEqual(ex.failures["child_unaccompanied"], 1)

    def test_validate_distinguishes_conflict_types(self):
        hh, ev = make_scenario("martin", "none")
        obs = Conditions.observed(hh, ev)
        plan = {"marie": opt(hh, obs, "marie", Mode.CAR, "lea"), "paul": opt(hh, obs, "paul", Mode.CAR, "lea"),
                "tom": opt(hh, obs, "tom", Mode.BIKE)}
        types = {v["type"] for v in validate(hh, obs, plan)}
        self.assertEqual(types, {"car_overclaim", "escort_duplicate"})


class ProtocolTests(unittest.TestCase):
    def test_rule_communication_resolves_car_conflict(self):
        off = run_episode("martin", "bus_strike", "rule", False)
        on = run_episode("martin", "bus_strike", "rule", True)
        self.assertGreater(off["metrics"]["intent_conflicts_initial"], 0)
        self.assertGreater(off["metrics"]["exec_car_unavailable"], 0)
        self.assertEqual(on["metrics"]["violations_committed"], 0)
        self.assertEqual(on["metrics"]["exec_car_unavailable"], 0)
        perfs = {m["performative"] for m in on["messages"]}
        self.assertTrue({"request", "propose", "counter", "accept", "reject", "commit"} <= perfs)

    def test_oracle_has_zero_regret_and_central_is_optimal_for_observed_view(self):
        for h in HOUSEHOLDS:
            for e in ("none", "bus_strike", "car_breakdown"):
                self.assertEqual(run_episode(h, e, "oracle", None)["metrics"]["regret"], 0)
                hh, ev = make_scenario(h, e)
                obs = Conditions.observed(hh, ev)
                best = execute(hh, central_plan(hh, obs), obs).household_cost
                rule = Episode(hh, ev, "rule", True, None)
                rule.run()
                self.assertLessEqual(best, execute(hh, rule.plan, obs).household_cost)

    def test_llm_policy_refuses_to_run_without_a_model(self):
        with self.assertRaises(ValueError):
            run_episode("martin", "none", "llm", True)

    def test_invalid_llm_output_is_a_labelled_fallback(self):
        r = run_episode("martin", "bus_strike", "llm", True, client=ScriptedLLM(fail=True))
        self.assertGreater(r["metrics"]["llm_invalid"], 0)
        self.assertEqual(r["metrics"]["llm_decisions"], 0)
        self.assertEqual(r["metrics"]["fallback_decisions"], r["metrics"]["llm_invalid"])

    def test_stubborn_negotiators_deadlock_and_protocol_tie_break_is_logged(self):
        client = ScriptedLLM({"reason": "mine", "action": "keep", "option": "none"})
        hh, ev = make_scenario("martin", "bus_strike")
        ep = Episode(hh, ev, "llm", True, client)
        ep.plan = {}
        # Force both parents to claim the car initially, then let them refuse to concede.
        obs = ep.obs
        ep.agents["marie"].decide = lambda *a, **k: (opt(hh, obs, "marie", Mode.CAR), _d("marie"))
        ep.agents["paul"].decide = lambda *a, **k: (opt(hh, obs, "paul", Mode.CAR, "lea"), _d("paul"))
        ep.agents["tom"].decide = lambda *a, **k: (opt(hh, obs, "tom", Mode.BIKE), _d("tom"))
        r = ep.run()
        self.assertEqual(r["metrics"]["deadlocks"], 1)
        self.assertEqual(r["metrics"]["protocol_fallbacks"], 1)
        self.assertEqual(r["metrics"]["violations_committed"], 0)

    def test_hybrid_gate(self):
        for e in ("none", "bus_strike"):
            r = run_episode("garcia", e, "hybrid", True, client=ScriptedLLM(pick_first=True))
            self.assertEqual(r["metrics"]["llm_calls"], 0, e)
        r = run_episode("garcia", "decoy", "hybrid", True, client=ScriptedLLM(pick_first=True))
        self.assertGreater(r["metrics"]["llm_calls"], 0)

    def test_seeds_are_reproducible(self):
        a = run_episode("dubois", "heavy_rain", "rule", True, seed=3)
        b = run_episode("dubois", "heavy_rain", "rule", True, seed=3)
        self.assertEqual(a["metrics"], {**b["metrics"], "wall_ms": a["metrics"]["wall_ms"]})
        self.assertNotEqual(make_scenario("dubois", "none", 1)[0].members[0].ready,
                            make_scenario("dubois", "none", 0)[0].members[0].ready + 999)

    def test_every_scenario_runs_with_rules(self):
        for h in HOUSEHOLDS:
            for e in EVENTS:
                for comm in (False, True):
                    r = run_episode(h, e, "rule", comm)
                    self.assertGreaterEqual(r["metrics"]["regret"], 0)


class InterpreterTests(unittest.TestCase):
    def test_correct_interpretation_lets_rules_avoid_the_broken_car(self):
        client = ScriptedLLM({"reason": "warning light", "effect": "car_unavailable", "member": "none",
                              "district": "none", "minutes": 0})
        r = run_episode("martin", "car_breakdown", "interp", True, client=client)
        self.assertTrue(r["interpretation"]["correct"])
        self.assertEqual(r["metrics"]["llm_calls"], 1)
        self.assertEqual(r["metrics"]["exec_car_unavailable"], 0)
        self.assertFalse(any(p["mode"] == "car" for p in r["plan"].values()))

    def test_incomplete_interpretation_is_rejected_and_logged(self):
        client = ScriptedLLM({"reason": "?", "effect": "member_no_trip", "member": "none", "district": "none", "minutes": 0})
        r = run_episode("martin", "no_trip", "interp", True, client=client)
        self.assertIn("rejected", r["interpretation"])
        self.assertFalse(r["interpretation"]["correct"])

    def test_interpreter_is_not_called_without_free_text(self):
        for e in ("none", "bus_strike"):
            r = run_episode("martin", e, "interp", True, client=ScriptedLLM(fail=True))
            self.assertEqual(r["metrics"]["llm_calls"], 0)


class LLMValidationTests(unittest.TestCase):
    def test_schema_check(self):
        s = choice_schema("option", ["O1", "O2"])
        _check({"reason": "x", "option": "O1"}, s)
        with self.assertRaises(ValueError):
            _check({"reason": "x", "option": "O9"}, s)
        with self.assertRaises(KeyError):
            _check({"option": "O1"}, s)


def _d(agent):
    from hmcoop.agents import Decision
    return Decision(agent, "initial", "-", "llm", "forced by test")


if __name__ == "__main__":
    unittest.main()
