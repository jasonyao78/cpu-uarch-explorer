# SPDX-License-Identifier: Apache-2.0
"""Deploy 环节契约（GB10 任务书 §3.4/§5.6）：幂等、重试一次、结构化失败。

守四条契约：
1. 远端摘要已匹配 → 不推送（幂等）；
2. 首次推送失败 → 重试一次后成功 → 正常返回；
3. 两次皆败 / 校验不符 → RunnerError(code=deploy-failed)，不留含糊状态；
4. 本地产物缺失 → 明确的 cross-build 前置提示（deploy-local-missing）。
全部 fake：假执行器（脚本化远端摘要）+ 假 push（可注入失败），不依赖 GB10。
"""

import hashlib
import tempfile
import unittest
from pathlib import Path

from runner.deploy import deploy_if_needed
from runner.errors import RunnerError
from runner.executor.local import ExecutionResult

PLATFORM = {
    "target": {"target_id": "gb10-fake", "transport": "ssh",
               "ssh_host": "gb10-fake", "ssh_remote_root": "~"},
    "probes": {"ptr_chase": {
        "local": "__LOCAL__",  # setUp 中替换为临时真实文件
        "remote": "~/cpu-uarch-probes/ptr_chase"}},
}


class FakeExecutor:
    """远端文件系统语义：内存 dict 存 sha256（None = 文件不存在）。"""

    def __init__(self, remote_sha):
        self._remote_sha = remote_sha

    def execute(self, argv, command_prefix=()):
        cmd = " ".join(str(a) for a in argv)
        if cmd.startswith("sha256sum"):
            path = cmd.split()[-1]
            if self._remote_sha is None:
                return ExecutionResult(1, "", "No such file", "fake")
            return ExecutionResult(0, f"{self._remote_sha}  {path}", "", "fake")
        return ExecutionResult(1, "", "unscripted", "fake")


class RecordingPush:
    def __init__(self, executor, fail_times=0, sha_when_pushed=None):
        self.calls = 0
        self._executor = executor
        self._fail_times = fail_times
        self._sha_when_pushed = sha_when_pushed

    def __call__(self):
        self.calls += 1
        if self.calls <= self._fail_times:
            raise RunnerError("deploy-failed", f"transient network error (attempt {self.calls})")
        # 推送生效：远端摘要变为正确值（或保持错误值以制造校验失败）
        self._executor._remote_sha = self._sha_when_pushed


class TestDeploy(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        local = Path(self._tmp.name) / "ptr_chase"
        local.write_bytes(b"\x7fELF fake aarch64 binary")
        self._sha = hashlib.sha256(local.read_bytes()).hexdigest()
        self.platform = {
            "target": PLATFORM["target"],
            "probes": {"ptr_chase": {"local": str(local), "remote": "~/cpu-uarch-probes/ptr_chase"}},
        }

    def tearDown(self):
        self._tmp.cleanup()

    def test_already_deployed_skips_push(self):
        ex = FakeExecutor(self._sha)
        push = RecordingPush(ex, sha_when_pushed=self._sha)
        remote = deploy_if_needed(self.platform, "ptr_chase", ex, push=push)
        self.assertEqual(push.calls, 0)
        self.assertEqual(remote, "~/cpu-uarch-probes/ptr_chase")

    def test_first_push_fails_second_succeeds(self):
        ex = FakeExecutor(None)
        push = RecordingPush(ex, fail_times=1, sha_when_pushed=self._sha)
        deploy_if_needed(self.platform, "ptr_chase", ex, push=push)
        self.assertEqual(push.calls, 2)

    def test_double_failure_is_structured(self):
        ex = FakeExecutor(None)
        push = RecordingPush(ex, fail_times=99, sha_when_pushed=self._sha)
        with self.assertRaises(RunnerError) as cm:
            deploy_if_needed(self.platform, "ptr_chase", ex, push=push)
        self.assertEqual(cm.exception.code, "deploy-failed")

    def test_sha_mismatch_after_push_rejected(self):
        ex = FakeExecutor(None)
        wrong = "0" * 64
        push = RecordingPush(ex, sha_when_pushed=wrong)  # 推送"成功"但摘要不符
        with self.assertRaises(RunnerError) as cm:
            deploy_if_needed(self.platform, "ptr_chase", ex, push=push)
        self.assertEqual(cm.exception.code, "deploy-failed")

    def test_local_binary_missing_is_explicit(self):
        self.platform["probes"]["ptr_chase"]["local"] = str(Path(self._tmp.name) / "nope")
        ex = FakeExecutor(None)
        with self.assertRaises(RunnerError) as cm:
            deploy_if_needed(self.platform, "ptr_chase", ex, push=lambda: None)
        self.assertEqual(cm.exception.code, "deploy-local-missing")


if __name__ == "__main__":
    unittest.main()
