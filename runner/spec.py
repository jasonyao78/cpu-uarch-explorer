# SPDX-License-Identifier: Apache-2.0
"""ExperimentSpec 与 platform 配置加载（轻校验，零依赖）。

完整 schema 校验是开发期动作（jsonschema 不入运行时依赖，ADR-0003 精神）；
这里只守住运行所必需的结构性前提，缺了就早报错。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import RunnerError


def _load_json(path: Path, what: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    except FileNotFoundError:
        raise RunnerError("config-missing", f"{what} not found: {path}")
    except json.JSONDecodeError as e:
        raise RunnerError("config-invalid", f"{what} is not valid JSON: {path}: {e}")
    if not isinstance(obj, dict):
        raise RunnerError("config-invalid", f"{what} must be a JSON object: {path}")
    return obj


def load_experiment(path: str | Path) -> dict[str, Any]:
    spec = _load_json(Path(path), "experiment spec")
    for key in ("schema_version", "id", "protocol_version", "harness", "metrics"):
        if key not in spec:
            raise RunnerError("config-invalid", f"experiment spec missing required key {key!r}: {path}")
    exe = spec.get("execution")
    if not isinstance(exe, dict) or "probe" not in exe or "sweep" not in exe:
        raise RunnerError("config-invalid",
                          f"experiment spec requires execution.probe and execution.sweep: {path}")
    return spec


def load_platform(path: str | Path) -> dict[str, Any]:
    cfg = _load_json(Path(path), "platform config")
    if "target" not in cfg:
        raise RunnerError("config-invalid", f"platform config missing 'target': {path}")
    target = cfg["target"]
    for key in ("os", "isa", "execution_kind", "executor", "target_id"):
        if key not in target:
            raise RunnerError("config-invalid",
                              f"platform target missing required key {key!r} (ADR-0006 正交分解): {path}")
    if "probes" not in cfg:
        raise RunnerError("config-invalid", f"platform config missing 'probes' map: {path}")
    return cfg
