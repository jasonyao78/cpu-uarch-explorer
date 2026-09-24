# SPDX-License-Identifier: Apache-2.0
"""Run 引擎：Plan → repeated execution → adapter → raw artifact → parser
→ statistics → atomic record（2026-09-24 评审裁定的最小纵向闭环）。

反模式对照（GB10 实证缺陷，逐条对冲）：
- samples 配置死参数 → repetitions 在此真实驱动循环，sample_index 递增；
- 静默参数降级 → 单位解析在 plan 期严格报错（resolve.py）；
- environment 硬编码 unknown → 每次运行采集真实 os/kernel/compiler + control；
- 宽泛 except 掩盖失败 → 异常映射为结构化 failure.reason，绝不吞掉；
- 输出打印请求值而非实际值 → raw_command 记录实际执行命令（含控制前缀）。
"""

from __future__ import annotations

from pathlib import Path

from .adapters.ptr_chase import PtrChaseAdapter
from .artifacts import ArtifactStore
from .errors import ParseError
from .executor.local import LocalExecutor
from .plan import Case, Plan
from .records import (JsonlWriter, build_run_record, compiler_version,  # noqa: F401
                      environment_block, git_provenance, write_json_atomic,
                      write_jsonl_atomic)
from .statistics import summarize

_ADAPTERS = {a.probe_name: a for a in (PtrChaseAdapter(),)}

# Probe ABI 退出码 → run 状态（ADR-0006 §3）
_EXIT_STATUS = {0: "ok", 1: "failed", 2: "unsupported"}


def _failure_reason(result) -> tuple[str, dict]:
    """把执行结果映射为 (status, failure)：超时空返回码、exit 2=unsupported、
    其余非零=failed，reason 为机器可读码（run-record v2 failure.reason）。"""
    if result.timed_out:
        return "failed", {"reason": "probe-timeout"}
    if result.returncode == 2:
        return "unsupported", {"reason": "capability-unsupported", "detail": result.stderr.strip()}
    if result.returncode is None:
        return "failed", {"reason": "spawn-error", "detail": result.stderr.strip()}
    return "failed", {"reason": f"probe-exit-{result.returncode}", "detail": result.stderr.strip()}


def run_plan(plan: Plan, platform: dict, run_dir: Path, repo_root: Path) -> dict:
    """执行整个 plan，逐 case 落 record；返回 run 汇总。任何 case 失败不中断后续 case。"""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    store = ArtifactStore(run_dir)
    records_path = run_dir / "records.jsonl"
    writer = JsonlWriter(records_path)
    executor = LocalExecutor()

    git = git_provenance(repo_root)
    probe_bin = Path(platform["probes"][plan.cases[0].probe])
    if not probe_bin.is_file():
        raise SystemExit(f"probe binary missing: {probe_bin} (run cmake --build build first)")
    bin_entry = store.register_probe_binary(probe_bin, git["commit"], git["dirty"])

    probe_meta = {
        "name": plan.cases[0].probe,
        "protocol_version": plan.protocol_version,
        "implementation_id": _ADAPTERS[plan.cases[0].probe].implementation_id,
        "git": git,
        "artifact": {"sha256": bin_entry["sha256"]},
    }

    summary = {"total": 0, "ok": 0, "failed": 0, "skipped": 0, "unsupported": 0}
    try:
        for case in plan.cases:
            record = _run_case(case, platform, probe_meta, executor, store, git)
            writer.append(record)
            summary["total"] += 1
            summary[record["status"]] += 1
            print(f"[{record['status']:>11}] {case.id} "
                  + (f"median={record['metrics'][0]['statistics']['median']:.3f} ns "
                     f"(n={record['metrics'][0]['repetitions']})"
                     if record["status"] == "ok" else record.get("failure", {}).get("reason", "")))
    finally:
        writer.close()

    write_jsonl_atomic(run_dir / "artifacts.jsonl", store.entries)
    write_json_atomic(run_dir / "run-manifest.json", {
        "schema_version": "1.0",
        "experiment_id": plan.experiment_id,
        "protocol_version": plan.protocol_version,
        "target": plan.target,
        "records": str(records_path.resolve()),
        "summary": summary,
    })
    return summary


def _run_case(case: Case, platform: dict, probe_meta: dict,
              executor: LocalExecutor, store: ArtifactStore, git: dict) -> dict:
    """执行单个 case：按 case.repetitions 重复执行（sample_index 递增），
    每趟原始输出落盘；全部成功才产 ok 记录（median 统计），任何失败产出
    status=failed/unsupported + 结构化 failure + 空 metrics（schema v2
    条件化约束），成功样本数写入 detail 供审计。"""
    adapter = _ADAPTERS[case.probe]
    probe_bin = str(Path(platform["probes"][case.probe]).resolve())
    params = {k: rv.value for k, rv in case.params}
    provenance = {k: rv.source for k, rv in case.params}
    argv = [probe_bin] + adapter.build_argv(params)
    env = environment_block(case.control.mechanism, case.control.value)

    latencies: list[float] = []
    raw_refs: list[str] = []
    first_failure: dict | None = None
    raw_command = ""
    for sample_index in range(case.repetitions):
        result = executor.execute(argv, case.control.command_prefix)
        raw_command = result.raw_command
        store.write_raw_sample(case.id, sample_index, result.stdout, result.stderr)
        raw_refs.append(f"raw-samples:{case.id.replace('/', '_').replace(':', '_')}.s{sample_index}")
        status = _EXIT_STATUS.get(result.returncode, "failed")
        if status != "ok":
            if first_failure is None:
                _, first_failure = _failure_reason(result)
            continue
        try:
            metrics = adapter.parse_output(result.stdout, result.stderr)
            latencies.append(metrics[0]["value"])
        except ParseError as e:
            if first_failure is None:
                first_failure = {"reason": "parse-error", "detail": str(e)}

    if latencies and first_failure is None:
        stats = summarize(latencies)
        metrics = [{
            "name": "latency_ns", "value": stats["median"], "unit": "ns",
            "repetitions": len(latencies), "statistics": stats,
            "raw_samples_ref": raw_refs[0],
        }]
        return build_run_record(status="ok", target=platform["target"], probe=probe_meta,
                                environment=env, params=params, params_provenance=provenance,
                                metrics=metrics, raw_command=raw_command)

    # 部分样本失败也按 failed 记（保守口径），成功样本数写进 detail 供审计
    failure = dict(first_failure or {"reason": "no-ok-samples"})
    failure["detail"] = (failure.get("detail", "") +
                         f" | ok_samples={len(latencies)}/{case.repetitions}").strip(" |")
    return build_run_record(status="failed" if failure["reason"] != "capability-unsupported" else "unsupported",
                            target=platform["target"], probe=probe_meta, environment=env,
                            params=params, params_provenance=provenance,
                            metrics=[], raw_command=raw_command, failure=failure)
