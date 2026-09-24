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

from pathlib import Path

from .adapters.ptr_chase import PtrChaseAdapter
from .artifacts import ArtifactStore
from .errors import ParseError
from .executor import make_executor
from .plan import Case, Plan
from .records import (JsonlWriter, build_run_record, environment_block,  # noqa: F401
                      git_provenance, write_json_atomic,
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


def _register_probe(store: ArtifactStore, executor, platform: dict,
                    probe_name: str, git: dict) -> tuple[str, dict]:
    """登记 probe 二进制 artifact，返回 (实际 argv 用的路径, manifest 条目)。

    local：读本机字节算 SHA256，argv 用绝对路径；ssh：路径相对远端仓库根
    （execute 会话内已 cd），SHA256 经执行器通道在目标机采集——本机读不到
    远端字节，也不允许假装读得到（OI-9 蓝图：artifact 锚定实际执行体）。"""
    configured = platform["probes"][probe_name]
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
    每趟原始输出落盘；全部成功才产 ok 记录（median 统计），任何失败产出
    status=failed/unsupported + 结构化 failure + 空 metrics（schema v2
    条件化约束），成功样本数写入 detail 供审计。"""
    adapter = _ADAPTERS[case.probe]
    params = {k: rv.value for k, rv in case.params}
    provenance = {k: rv.source for k, rv in case.params}
    argv = [probe_path] + adapter.build_argv(params)
    env = environment_block(case.control.mechanism, case.control.value, system_info)

    # 频率快照（measurement-discipline §5；2026-09-25 讨论裁定"快照先行"）：
    # 锁频落地前，每条记录至少能回答"测量时核频多少"。瞬时值非区间精确
    # 频率；采集失败则省略字段，不编造。environment.freq_snapshot 为登记的
    # schema 扩展字段（runner/schema/README.md）。
    cpu_hint = case.control.value if case.control.mechanism == "taskset" else "0"
    snap_before = executor.freq_snapshot(cpu_hint)

    latencies: list[float] = []
    raw_refs: list[str] = []
    first_failure: dict | None = None
    first_ok_extra: dict | None = None  # adapter 附加字段（如 page_policy）随 metric 入档
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
            if first_ok_extra is None:
                first_ok_extra = {k: v for k, v in metrics[0].items()
                                  if k not in ("name", "value", "unit")}
        except ParseError as e:
            if first_failure is None:
                first_failure = {"reason": "parse-error", "detail": str(e)}

    # 频率快照必须在 ok/failed 两条 return 路径之前入 env——放晚了 ok 路径
    # 直接 return 会漏（2026-09-25 复测自证：首跑 12 条记录全无快照）。
    snap_after = executor.freq_snapshot(cpu_hint)
    if snap_before is not None or snap_after is not None:
        env["freq_snapshot"] = {"before_hz": snap_before, "after_hz": snap_after}

    if latencies and first_failure is None:
        stats = summarize(latencies)
        metrics = [{
            "name": "latency_ns", "value": stats["median"], "unit": "ns",
            "repetitions": len(latencies), "statistics": stats,
            "raw_samples_ref": raw_refs[0],
            **(first_ok_extra or {}),
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
