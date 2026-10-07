# SPDX-License-Identifier: Apache-2.0
"""Run 引擎：Plan → repeated execution → adapter → raw artifact → parser
→ statistics → atomic record（2026-09-24 评审裁定的最小纵向闭环）。

2026-09-25 扩展（Xeon 接入任务）：执行器按 platform.target.transport
经 make_executor 选择（ADR-0006 正交分解），主流程对传输层零特判。
环境信息（os/kernel/compiler）由执行器通道采集——ssh 平台的记录描述
的是目标机而非本机；远端 probe 二进制的 SHA256 同样经执行器通道在
目标机采集（artifact 锚定实际执行的那份二进制）。

反模式对照（GB10 实证缺陷，逐条对冲）：
- samples 配置死参数 → repetitions 在此真实驱动循环，sample_index 递增；
- 静默参数降级 → 单位解析在 plan 期严格报错（resolve.py）；
- environment 硬编码 unknown → 每次运行由执行器采集真实 os/kernel/compiler + control；
- 宽泛 except 掩盖失败 → 异常映射为结构化 failure.reason，绝不吞掉；
- 输出打印请求值而非实际值 → raw_command 记录实际执行命令（含控制前缀）。
"""

from __future__ import annotations

import math
from pathlib import Path

from .adapters.ptr_chase import PtrChaseAdapter
from .artifacts import ArtifactStore
from .errors import ParseError, RunnerError
from .environment.policy import (collect_environment_state,
                                 evaluate_preconditions_full,
                                 evaluate_stability_full)
from .executor import make_executor
from .plan import Case, Plan
from .records import (JsonlWriter, build_run_record, environment_block,  # noqa: F401
                      git_provenance, write_json_atomic,
                      write_jsonl_atomic)
from .statistics import summarize

_ADAPTERS = {a.probe_name: a for a in (PtrChaseAdapter(),)}

# Probe ABI 退出码 → run 状态（ADR-0006 §3）
_EXIT_STATUS = {0: "ok", 1: "failed", 2: "unsupported"}


def _aggregate_sample_metrics(
        samples: list[tuple[int, str, list[dict]]]) -> list[dict]:
    """Aggregate adapter metrics without discarding per-process evidence.

    Every repetition must expose the same unique metric names and units. Each
    raw value and its adapter-provided fields remain in ``observations``;
    additional fields are copied to metric top level only when invariant over
    all repetitions. This prevents first-sample metadata from masquerading as
    a property of the complete case.
    """
    if not samples:
        raise ParseError("cannot aggregate an empty sample set")

    first_metrics = samples[0][2]
    order = [metric.get("name") for metric in first_metrics]
    if not order or any(not isinstance(name, str) or not name for name in order):
        raise ParseError("every metric must have a non-empty string name")
    if len(set(order)) != len(order):
        raise ParseError(f"duplicate metric names in sample 0: {order!r}")

    indexed_samples: list[tuple[int, str, dict[str, dict]]] = []
    for sample_index, raw_ref, metrics in samples:
        by_name: dict[str, dict] = {}
        for metric in metrics:
            name = metric.get("name")
            if not isinstance(name, str) or not name:
                raise ParseError(
                    f"sample {sample_index} metric has no valid name: {metric!r}"
                )
            if name in by_name:
                raise ParseError(
                    f"sample {sample_index} has duplicate metric {name!r}"
                )
            if "value" not in metric or "unit" not in metric:
                raise ParseError(
                    f"sample {sample_index} metric {name!r} lacks value/unit"
                )
            value = metric["value"]
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value)):
                raise ParseError(
                    f"sample {sample_index} metric {name!r} has non-finite "
                    f"numeric value {value!r}"
                )
            by_name[name] = metric
        if set(by_name) != set(order):
            raise ParseError(
                f"sample {sample_index} metric set mismatch: "
                f"expected {sorted(order)!r}, got {sorted(by_name)!r}"
            )
        indexed_samples.append((sample_index, raw_ref, by_name))

    aggregated: list[dict] = []
    reserved = {
        "name", "value", "unit", "sample_index", "raw_sample_ref",
        "observations", "statistics", "repetitions", "raw_samples_ref",
    }
    for name in order:
        metrics = [by_name[name] for _, _, by_name in indexed_samples]
        unit = metrics[0]["unit"]
        if any(metric["unit"] != unit for metric in metrics[1:]):
            raise ParseError(f"metric {name!r} unit differs across samples")
        values = [metric["value"] for metric in metrics]
        stats = summarize(values)
        observations = []
        for (sample_index, raw_ref, _), metric in zip(indexed_samples, metrics):
            observation = {
                "sample_index": sample_index,
                "value": metric["value"],
                "raw_sample_ref": raw_ref,
            }
            observation.update({
                key: value for key, value in metric.items() if key not in reserved
            })
            observations.append(observation)

        aggregate = {
            "name": name,
            "value": stats["median"],
            "unit": unit,
            "repetitions": len(metrics),
            "statistics": stats,
            "raw_samples_ref": samples[0][1],
            "observations": observations,
        }
        first_extra = {
            key: value for key, value in metrics[0].items() if key not in reserved
        }
        for key, value in first_extra.items():
            if all(key in metric and metric[key] == value for metric in metrics[1:]):
                aggregate[key] = value
        aggregated.append(aggregate)
    return aggregated


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


def _register_probe(store: ArtifactStore, executor, platform: dict,
                    probe_name: str, git: dict) -> tuple[str, dict]:
    """登记 probe 二进制 artifact，返回 (实际 argv 用的路径, manifest 条目)。

    local：读本机字节算 SHA256，argv 用绝对路径；ssh：路径相对远端仓库根
    （execute 会话内已 cd），SHA256 经执行器通道在目标机采集——本机读不到
    远端字节，也不允许假装读得到（OI-9 蓝图：artifact 锚定实际执行体）。"""
    configured = platform["probes"][probe_name]
    if isinstance(configured, dict):
        # deploy 模式（GB10 三机管线，任务书 §3.4）：本地交叉编译产物 →
        # 幂等推送目标机并 SHA256 校验；artifact 锚定本地实物的摘要
        from .deploy import deploy_if_needed, _local_sha256
        remote_path = deploy_if_needed(platform, probe_name, executor)
        return (remote_path,
                store.register_probe_binary_digest(
                    remote_path, _local_sha256(Path(configured["local"])),
                    git["commit"], git["dirty"]))
    if platform["target"].get("transport", "local") == "local":
        probe_bin = Path(configured)
        if not probe_bin.is_file():
            raise SystemExit(f"probe binary missing: {probe_bin} (run cmake --build build first)")
        return (str(probe_bin.resolve()),
                store.register_probe_binary(probe_bin, git["commit"], git["dirty"]))
    res = executor.execute(["sha256sum", configured])
    digest = res.stdout.split()[0] if res.returncode == 0 and res.stdout.split() else None
    if digest is None or len(digest) != 64:
        raise SystemExit(f"remote probe binary missing or unreadable: {configured} "
                         f"(via ssh; stderr: {res.stderr.strip()[:200]})")
    return (configured,
            store.register_probe_binary_digest(configured, digest, git["commit"], git["dirty"]))


def run_plan(plan: Plan, platform: dict, run_dir: Path, repo_root: Path) -> dict:
    """执行整个 plan，逐 case 落 record；返回 run 汇总。任何 case 失败不中断后续 case。"""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    store = ArtifactStore(run_dir)
    records_path = run_dir / "records.jsonl"
    writer = JsonlWriter(records_path)
    executor = make_executor(platform)

    git = git_provenance(repo_root)
    probe_path, bin_entry = _register_probe(store, executor, platform, plan.cases[0].probe, git)
    # 环境信息由执行器通道一次采集：ssh 平台描述目标机，local 描述本机
    system_info = executor.system_info()

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
            record = _run_case(case, platform, probe_meta, probe_path, executor,
                               store, system_info, git)
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


def _run_case(case: Case, platform: dict, probe_meta: dict, probe_path: str,
              executor, store: ArtifactStore, system_info: dict, git: dict) -> dict:
    """执行单个 case：按 case.repetitions 重复执行（sample_index 递增），
    每趟原始输出落盘；全部成功才按 metric name 聚合并保留逐样本 observation，
    任何失败产出 status=failed/unsupported + 结构化 failure + 空 metrics
    （schema v2 条件化约束），成功样本数写入 detail 供审计。"""
    adapter = _ADAPTERS[case.probe]
    params = {k: rv.value for k, rv in case.params}
    provenance = {k: rv.source for k, rv in case.params}
    argv = [probe_path] + adapter.build_argv(params)
    env = environment_block(case.control.mechanism, case.control.value, system_info)
    environment_policy = platform.get("measurement_environment")
    state_before: dict | None = None
    if environment_policy is not None:
        try:
            state_before = collect_environment_state(executor, environment_policy)
            violations, env_warnings = evaluate_preconditions_full(
                state_before, environment_policy)
        except RunnerError as error:
            env["state_snapshot"] = {
                "policy_result": {"valid": False, "stage": "before",
                                  "violations": [error.code]},
            }
            return build_run_record(
                status="failed", target=platform["target"], probe=probe_meta,
                environment=env, params=params, params_provenance=provenance,
                metrics=[], raw_command="",
                failure={"reason": "environment-snapshot-failed", "detail": str(error)})
        env["state_snapshot"] = {
            "before": state_before,
            "policy_result": {"valid": not violations, "stage": "before",
                              "violations": violations,
                              "accepted_nonbaseline": env_warnings},
        }
        if violations:
            return build_run_record(
                status="failed", target=platform["target"], probe=probe_meta,
                environment=env, params=params, params_provenance=provenance,
                metrics=[], raw_command="",
                failure={"reason": "environment-precondition-failed",
                         "detail": ",".join(violations)})

    # 频率快照（measurement-discipline §5；2026-09-25 讨论裁定"快照先行"）：
    # 锁频落地前，每条记录至少能回答"测量时核频多少"。瞬时值非区间精确
    # 频率；采集失败则省略字段，不编造。environment.freq_snapshot 为登记的
    # schema 扩展字段（runner/schema/README.md）。
    cpu_hint = case.control.value if case.control.mechanism == "taskset" else "0"
    snap_before = executor.freq_snapshot(cpu_hint)

    # 辅助快照（GB10 任务书 §5.4：CPU/GPU 共享内存控制器，GPU 负载会干扰
    # 内存测量——平台配置 aux_snapshots 声明只读采集命令，run 前后各一次）。
    # 通用机制零平台特判：命令来自配置，引擎不识别 nvidia-smi。
    aux_entries = platform.get("aux_snapshots", []) or []
    aux_before: dict = {}
    for aux in aux_entries:
        r = executor.execute(aux["command"])
        if r.returncode == 0:
            aux_before[aux["name"]] = r.stdout.strip()[:200]

    sample_metrics: list[tuple[int, str, list[dict]]] = []
    first_ok_stdout: str | None = None
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
            # MB-06：requested→realized 一致性核验——plan case_params 随
            # 解析传入，探针自描述与请求不符即 ParseError（执行漂移不进证据）
            metrics = adapter.parse_output(result.stdout, result.stderr, params)
            if first_ok_stdout is None:
                first_ok_stdout = result.stdout
            sample_metrics.append((sample_index, raw_refs[-1], metrics))
        except ParseError as e:
            if first_failure is None:
                first_failure = {"reason": "parse-error", "detail": str(e)}

    # 频率快照必须在 ok/failed 两条 return 路径之前入 env——放晚了 ok 路径
    # 直接 return 会漏（2026-09-25 复测自证：首跑 12 条记录全无快照）。
    snap_after = executor.freq_snapshot(cpu_hint)
    if snap_before is not None or snap_after is not None:
        env["freq_snapshot"] = {"before_hz": snap_before, "after_hz": snap_after}
    if aux_entries:
        aux_after: dict = {}
        for aux in aux_entries:
            r = executor.execute(aux["command"])
            if r.returncode == 0:
                aux_after[aux["name"]] = r.stdout.strip()[:200]
        merged = {name: {"before": aux_before.get(name), "after": aux_after.get(name)}
                  for name in set(aux_before) | set(aux_after)}
        if merged:
            env["aux_snapshots"] = merged

    if environment_policy is not None:
        try:
            state_after = collect_environment_state(executor, environment_policy)
            post_violations, post_warnings = evaluate_preconditions_full(
                state_after, environment_policy)
            drift_violations, drift_warnings = evaluate_stability_full(
                state_before, state_after, environment_policy)
            post_violations = sorted(set(post_violations) | set(drift_violations))
            post_warnings = sorted(set(post_warnings) | set(drift_warnings))
        except RunnerError as error:
            env["state_snapshot"]["policy_result"] = {
                "valid": False, "stage": "after", "violations": [error.code]}
            return build_run_record(
                status="failed", target=platform["target"], probe=probe_meta,
                environment=env, params=params, params_provenance=provenance,
                metrics=[], raw_command=raw_command,
                failure={"reason": "environment-snapshot-failed", "detail": str(error)})
        env["state_snapshot"]["after"] = state_after
        env["state_snapshot"]["policy_result"] = {
            "valid": not post_violations, "stage": "after",
            "violations": post_violations,
            "accepted_nonbaseline": post_warnings}
        if post_violations:
            return build_run_record(
                status="failed", target=platform["target"], probe=probe_meta,
                environment=env, params=params, params_provenance=provenance,
                metrics=[], raw_command=raw_command,
                failure={"reason": "environment-postcondition-failed",
                         "detail": ",".join(post_violations)})

    if sample_metrics and first_failure is None:
        try:
            metrics = _aggregate_sample_metrics(sample_metrics)
        except ParseError as error:
            first_failure = {"reason": "metric-aggregation-error", "detail": str(error)}
        else:
            # PA-02：realized descriptor 随结构化记录持久化（requested=params
            # 已入档；realized=探针自描述激励审计，schema 登记扩展）。
            parse_realized = getattr(adapter, "parse_realized", None)
            realized = parse_realized(first_ok_stdout or "") \
                if parse_realized is not None else {}
            probe_block = dict(probe_meta)
            if realized:
                probe_block["realized"] = realized
            return build_run_record(
                status="ok", target=platform["target"], probe=probe_block,
                environment=env, params=params, params_provenance=provenance,
                metrics=metrics, raw_command=raw_command,
            )

    # 部分样本失败也按 failed 记（保守口径），成功样本数写进 detail 供审计
    failure = dict(first_failure or {"reason": "no-ok-samples"})
    failure["detail"] = (failure.get("detail", "") +
                         f" | ok_samples={len(sample_metrics)}/{case.repetitions}").strip(" |")
    return build_run_record(status="failed" if failure["reason"] != "capability-unsupported" else "unsupported",
                            target=platform["target"], probe=probe_meta, environment=env,
                            params=params, params_provenance=provenance,
                            metrics=[], raw_command=raw_command, failure=failure)
