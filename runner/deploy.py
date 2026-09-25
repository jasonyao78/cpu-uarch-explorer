# SPDX-License-Identifier: Apache-2.0
"""Deploy 环节：交叉编译产物的目标机分发与 SHA256 校验（GB10 接入任务 §3.4）。

三机管线（Mac 驱动 → Xeon 交叉编译 → GB10 执行）中，本平台负责把二进制
推到目标机约定路径并以 SHA256 校验——与 artifact-manifest 同一摘要口径
（requested/actual 纪律）。失败语义：传输或校验失败**重试一次**（任务书
§5.6：网络抖动不动玷污数据档案），二次失败抛结构化 RunnerError
（deploy-failed）——绝不留下"以为已部署"的含糊状态。

平台配置形态（probes 映射的 dict 形式触发 deploy；str 维持原语义）：

    "probes": { "ptr_chase": {
        "local":  "build/linux-aarch64/release/probes/cache-mem/ptr_chase",
        "remote": "~/cpu-uarch-probes/ptr_chase" } }
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .errors import RunnerError
from .executor.ssh import SshExecutor

_DEFAULT_RETRIES = 1  # 任务书 §5.6：容忍一次重试，二次失败才记 failed


def _local_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _remote_sha256(executor, remote_path: str) -> str | None:
    res = executor.execute(["sha256sum", remote_path])
    if res.returncode != 0 or not res.stdout.split():
        return None
    digest = res.stdout.split()[0]
    return digest if len(digest) == 64 else None


def _default_push(platform: dict, local_path: Path, remote_path: str) -> None:
    """scp 推送（BatchMode 硬失败语义同 SshExecutor）；推送前确保远端目录。"""
    import subprocess
    host = platform["target"].get("ssh_host")
    if not host:
        raise RunnerError("deploy-failed", "deploy requires target.ssh_host (ssh config alias)")
    executor = SshExecutor(host, platform["target"].get("ssh_remote_root", "~"))
    parent = str(remote_path).rsplit("/", 1)[0] or "~"
    res = executor.execute(["mkdir", "-p", parent])
    if res.returncode != 0:
        raise RunnerError("deploy-failed", f"remote mkdir -p {parent} failed: {res.stderr.strip()[:120]}")
    res = subprocess.run(["scp", "-o", "BatchMode=yes", str(local_path), f"{host}:{remote_path}"],
                         capture_output=True, text=True)
    if res.returncode != 0:
        raise RunnerError("deploy-failed", f"scp failed: {res.stderr.strip()[:160]}")


def deploy_if_needed(platform: dict, probe_name: str, executor, *,
                     push=None, retries: int = _DEFAULT_RETRIES) -> str:
    """幂等部署：远端摘要匹配则跳过；否则推送 + 校验，失败重试 retries 次。
    返回远端路径（engine 用作 argv 路径）。"""
    entry = platform["probes"][probe_name]
    if not isinstance(entry, dict):
        raise RunnerError("deploy-config-invalid",
                          f"probe {probe_name!r} is not a deploy entry (no local/remote)")
    local_path = Path(entry["local"])
    remote_path = entry["remote"]
    if not local_path.is_file():
        raise RunnerError("deploy-local-missing",
                          f"local probe binary missing: {local_path} (cross-build first, see runbook)")
    want = _local_sha256(local_path)
    push = push or (lambda: _default_push(platform, local_path, remote_path))

    if _remote_sha256(executor, remote_path) == want:
        return remote_path
    last_err: str = ""
    for attempt in range(retries + 1):
        try:
            push()
        except RunnerError as e:
            last_err = str(e)
            continue
        if _remote_sha256(executor, remote_path) == want:
            return remote_path
        last_err = "sha256 mismatch after push"
    raise RunnerError("deploy-failed",
                      f"{probe_name}: {last_err} (retried {retries}x) — "
                      "check ssh alias/network and remote writability")
