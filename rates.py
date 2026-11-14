"""Single source of truth for model pricing (USD per 1,000,000 tokens).

Every dollar figure in this repository resolves to the table below: the live
savings ledger in ``stats.py``, the audited benchmark in ``bench/runner.py``, and
the numbers quoted in ``README.md`` / ``bench/BENCHMARK_REPORT.md``. Change a
rate here and the whole package follows. Never restate a price in a second file.

Verified against ``GET https://inference-api.nousresearch.com/v1/models`` on
2026-11-14. ``input`` is the prompt rate, ``output`` the completion rate, and
``cache_read`` the provider's cache-read (KV hit) rate. Providers reprice: if
your contract differs, point ``STAGEHANDS_RATES_JSON`` at a JSON file of
overrides (``{"<model>": {"input": x, "output": y, "cache_read": z}}``) instead
of editing call sites.
"""
from __future__ import annotations

import json
import os
from typing import Any

SOVEREIGN_MODEL = "google/gemini-4-argon"

# model -> USD per 1M tokens
MODEL_RATES: dict[str, dict[str, Any]] = {
    SOVEREIGN_MODEL: {
        "input": 2.00,
        "output": 10.00,
        "cache_read": 0.10,
        "role": "Sovereign Voice (Audi)",
    },
    "deepseek/deepseek-v4-pro": {
        "input": 0.94,
        "output": 1.89,
        "cache_read": 0.08,
        "role": "Stagehand (analyst)",
    },
    "deepseek/deepseek-v4.1-flash": {
        "input": 0.106,
        "output": 0.513,
        "cache_read": 0.004,
        "role": "Stagehand (code_monkey)",
    },
    "deepseek/deepseek-v4-flash": {
        "input": 0.09,
        "output": 0.18,
        "cache_read": 0.018,
        "role": "Stagehand (scout / briefer)",
    },
    "qwen/qwen3.7-flash": {
        "input": 0.03,
        "output": 0.13,
        "cache_read": 0.006,
        "role": "Stagehand (librarian)",
    },
    "anthropic/claude-haiku-5.5": {
        "input": 0.10,
        "output": 0.50,
        "cache_read": 0.01,
        "role": "Stagehand (adversary)",
    },
}

OVERRIDE_ENV = "STAGEHANDS_RATES_JSON"


def _apply_overrides(table: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Merge optional deployment-specific overrides from STAGEHANDS_RATES_JSON."""
    raw = os.environ.get(OVERRIDE_ENV)
    if not raw:
        return table
    try:
        data = json.loads(open(raw, encoding="utf-8").read()) if os.path.exists(raw) else json.loads(raw)
    except Exception:
        return table
    if not isinstance(data, dict):
        return table
    merged = {k: dict(v) for k, v in table.items()}
    for model, override in data.items():
        if not isinstance(override, dict):
            continue
        merged.setdefault(model, {}).update(override)
    return merged


MODEL_RATES = _apply_overrides(MODEL_RATES)


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[mid], 4)
    return round((ordered[mid - 1] + ordered[mid]) / 2.0, 4)


# Back-compat aliases used across the package.
ARGON_INPUT_USD_PER_M = MODEL_RATES[SOVEREIGN_MODEL]["input"]  # 2.00 list prompt rate
ARGON_UNCACHED_INPUT_USD_PER_M = ARGON_INPUT_USD_PER_M  # a cache miss pays list
ARGON_CACHED_INPUT_USD_PER_M = MODEL_RATES[SOVEREIGN_MODEL]["cache_read"]  # 0.10 on a KV hit
ARGON_OUTPUT_USD_PER_M = MODEL_RATES[SOVEREIGN_MODEL]["output"]

_WORKER_INPUTS = [v["input"] for m, v in MODEL_RATES.items() if m != SOVEREIGN_MODEL]
_WORKER_OUTPUTS = [v["output"] for m, v in MODEL_RATES.items() if m != SOVEREIGN_MODEL]
WORKER_INPUT_USD_PER_M = _median(_WORKER_INPUTS)  # roster median, not a guess
WORKER_OUTPUT_USD_PER_M = _median(_WORKER_OUTPUTS)

# bench/runner.py consumes this exact shape.
RATES = {
    model: {"input": v["input"], "output": v["output"], "role": v.get("role", model)}
    for model, v in MODEL_RATES.items()
}

if ARGON_CACHED_INPUT_USD_PER_M >= ARGON_INPUT_USD_PER_M:
    raise ValueError(
        "pricing sanity: cached input must be cheaper than the uncached list rate "
        f"({ARGON_CACHED_INPUT_USD_PER_M} >= {ARGON_INPUT_USD_PER_M})"
    )
