"""Regressions for catalog review: clean import and profile isolation."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HERMES_ROOT = Path('/usr/local/lib/hermes-agent')
for path in (ROOT, HERMES_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


class ReviewRegressions(unittest.TestCase):
    def test_plugin_loads_without_pyyaml(self):
        # Run a fresh interpreter, rejecting all PyYAML imports even if installed.
        script = '''
import builtins, importlib.util, sys
sys.path[:0] = [sys.argv[1], sys.argv[2]]
real_import = builtins.__import__
def block_yaml(name, *args, **kwargs):
    if name == "yaml" or name.startswith("yaml."):
        raise ModuleNotFoundError("No module named yaml")
    return real_import(name, *args, **kwargs)
builtins.__import__ = block_yaml
spec = importlib.util.spec_from_file_location("stagehands_init", sys.argv[1] + "/__init__.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
from pathlib import Path
from tempfile import TemporaryDirectory
with TemporaryDirectory() as td:
    cfg = Path(td) / "config.yaml"
    mod._write_raw_config(cfg, {"compression": {"protect_last_n": 20}}, explicit_path=True)
    _, data = mod._read_raw_config(cfg)
    assert data["compression"]["protect_last_n"] == 20
print("plugin loaded and config round-tripped")
'''
        run = subprocess.run([sys.executable, '-c', script, str(ROOT), str(HERMES_ROOT)],
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('plugin loaded', run.stdout)

    def test_context_local_home_wins_over_poisoned_environment(self):
        import hermes_constants
        import stats

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            local_home = root / 'local'
            local_home.mkdir()
            local_db = local_home / 'state.db'
            local_db.touch()
            wrong_home = root / 'wrong'
            wrong_home.mkdir()
            wrong_db = wrong_home / 'state.db'
            wrong_db.touch()
            with patch.dict(os.environ, {'HERMES_HOME': str(wrong_home),
                                         'HERMES_STATE_DB': str(wrong_db),
                                         'HERMES_PROFILE': 'another'}):
                token = hermes_constants.set_hermes_home_override(local_home)
                try:
                    self.assertEqual(stats.resolve_state_db(), local_db)
                    local_db.unlink()
                    self.assertIsNone(stats.resolve_state_db())
                    self.assertEqual(stats.resolve_state_db(wrong_db), wrong_db)
                    self.assertIsNone(stats.resolve_state_db(root / 'missing'))
                finally:
                    hermes_constants.reset_hermes_home_override(token)


class TestV2CleanupRegressions(unittest.TestCase):
    """Guards the 2026-11-14 cleanup pass: distinct analyst, one price table, fenced briefs."""

    def _provider(self):
        import sys
        from pathlib import Path
        repo = str(Path(__file__).resolve().parent.parent)
        if repo not in sys.path:
            sys.path.insert(0, repo)
        import provider
        return provider

    def test_analyst_is_not_code_monkey_under_another_name(self):
        provider = self._provider()
        analyst = provider.DEFAULT_WORKERS["analyst"]
        monkey = provider.DEFAULT_WORKERS["code_monkey"]
        self.assertNotEqual(analyst["model"], monkey["model"])
        self.assertNotEqual(analyst["reasoning_effort"], monkey["reasoning_effort"])

    def test_analyst_routes_by_default(self):
        provider = self._provider()
        route = provider.StagehandsProvider().route_task({"worker": "analyst"}, {})
        self.assertEqual(route["label"], "analyst")
        self.assertEqual(route["model"], provider.DEFAULT_WORKERS["analyst"]["model"])

    def test_route_redaction_masks_credentials_without_mutating(self):
        provider = self._provider()
        original = {"model": "m", "api_key": "sk-live-secret"}
        shown = provider.redact_route(original)
        self.assertEqual(shown["api_key"], "***redacted***")
        self.assertEqual(original["api_key"], "sk-live-secret")  # caller's dict untouched

    def test_parent_guidance_fences_worker_briefs(self):
        provider = self._provider()
        text = provider.StagehandsProvider().description({})
        self.assertIn("<backstage-brief>", text)
        self.assertIn("untrusted", text)
        self.assertIn("analyst", text)

    def test_pricing_resolves_to_exactly_one_table(self):
        import sys
        from pathlib import Path
        repo = Path(__file__).resolve().parent.parent
        for extra in (str(repo), str(repo / "bench")):
            if extra not in sys.path:
                sys.path.insert(0, extra)
        import rates, stats, runner
        argon = rates.MODEL_RATES[rates.SOVEREIGN_MODEL]
        self.assertEqual(stats.ARGON_INPUT_USD_PER_M, argon["input"])
        self.assertEqual(stats.ARGON_CACHED_INPUT_USD_PER_M, argon["cache_read"])
        self.assertEqual(runner.RATES[rates.SOVEREIGN_MODEL]["input"], argon["input"])
        self.assertEqual(runner.RATES[rates.SOVEREIGN_MODEL]["output"], argon["output"])
        for model, row in rates.MODEL_RATES.items():
            self.assertLess(row["cache_read"], row["input"], model)

    def test_effective_rate_never_exceeds_list_nor_dips_below_cached(self):
        import sys
        from pathlib import Path
        repo = str(Path(__file__).resolve().parent.parent)
        if repo not in sys.path:
            sys.path.insert(0, repo)
        import rates, stats, inspect
        src = inspect.getsource(stats)
        self.assertIn("ARGON_UNCACHED_INPUT_USD_PER_M * (1.0 - cache_hit_rate)", src)
        self.assertLess(rates.ARGON_CACHED_INPUT_USD_PER_M, rates.ARGON_UNCACHED_INPUT_USD_PER_M)
        self.assertEqual(rates.ARGON_UNCACHED_INPUT_USD_PER_M, rates.ARGON_INPUT_USD_PER_M)
