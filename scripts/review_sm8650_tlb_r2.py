#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""复核 2026-09-30 r2 评审的静态缺陷，不执行 JIT 或目标板测量。

输入为待评审源码树；仅在临时目录编译两段调用原型函数的 harness。
所有地址、计数和几何示例均为合成输入，输出不能作为硬件探测数据。
退出 0 表示这些缺陷在输入源码中被复现；源码修正后应重新评估本脚本。
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile


def candidate_index(va: int, hypothesis: int) -> int:
    """重放原型 H1-H4，输入合成 VA，返回候选索引。"""
    vpn = va >> 12
    return (vpn ^ (vpn >> 8 if hypothesis in (2, 4) else 0)
            ^ (vpn >> 16 if hypothesis in (3, 4) else 0)) & 255


def run_harness(compiler: str, directory: Path, name: str,
                source: str, flags: list[str]) -> subprocess.CompletedProcess:
    """在临时目录编译并运行只做函数复核的 harness；编译失败显式抛错。"""
    path = directory / f"{name}.c"
    binary = directory / name
    path.write_text(source)
    subprocess.run([compiler, *flags, str(path), "-o", str(binary)],
                   check=True, capture_output=True, text=True)
    return subprocess.run([str(binary)], capture_output=True, text=True,
                          timeout=10)


def main() -> int:
    """复现四类静态缺陷并打印结果；不会修改输入源码树。"""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source-tree", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_tree.resolve()
    deep = root / "docs/cpu-uarch-deep-analysis"
    tlb = deep / "tlb-deep-analysis/probes/l2_set_probe.c"
    rob = deep / "rob-deep-analysis/probes/rob_window_probe.c"
    compiler = shutil.which("clang")
    if compiler is None or not tlb.is_file() or not rob.is_file():
        parser.error("需要 clang 以及待评审的两个原型源文件")

    with tempfile.TemporaryDirectory(prefix="cpu-uarch-review-") as temp:
        directory = Path(temp)
        zero = run_harness(compiler, directory, "zero", f"""
#define main original_probe_main
#include {json.dumps(str(tlb))}
#undef main
int main(void) {{
    uintptr_t va = 0;
    return collect_set_addrs(1, 0, 0, (char *)(uintptr_t)0x100000000ull,
                             65536, &va);
}}
""", ["-O0", "-fsanitize=undefined", "-fno-sanitize-recover=undefined"])
        confirmed = zero.returncode != 0 and "division by zero" in zero.stderr
        print(f"w=0 division by zero confirmed: {confirmed}")
        if not confirmed:
            raise RuntimeError("w=0 缺陷未复现，须重新审阅源码")
        print(zero.stderr.strip())

        branch = run_harness(compiler, directory, "branch", f"""
#define main original_probe_main
#include {json.dumps(str(rob))}
#undef main
int main(void) {{
    insn_t words[2048];
    size_t n = build_routine(words, 2048, C_NOP, ANCHOR_MISS, 384, 2,
                             0x100000, 0x200000, 0x300000);
    long loop = -1;
    for (size_t i = 0; i < n; i++)
        if (words[i] == E_LDR(0, 0)) {{ loop = (long)i; break; }}
    size_t pc = n - 2;
    int32_t imm = (int32_t)((words[pc] >> 5) & 0x7ffffu);
    if (imm & (1 << 18)) imm -= 1 << 19;
    printf("ROB branch: expected=%ld actual=%ld (instruction indices)\\n",
           loop, (long)pc + imm);
    return ((long)pc + imm == loop) ? 1 : 0;
}}
""", ["-O0"])
        if branch.returncode != 0:
            raise RuntimeError("ROB 分支缺陷未复现，须重新审阅源码")
        print(branch.stdout.strip())

    base = 0x100000000
    for hypothesis in range(1, 5):
        chosen, page = [], 1
        while len(chosen) < 512:
            if candidate_index(base + page * 4096, hypothesis) not in (7, 100):
                chosen.append(page)
            page += 1
        print(f"filler H{hypothesis}: last_page={chosen[-1]}, "
              f"mapped=0..511, outside={sum(i >= 512 for i in chosen)}")
    for hypothesis, other in ((3, 1), (4, 2)):
        delta = Counter(candidate_index(base + i * 4096, hypothesis)
                        ^ candidate_index(base + i * 4096, other)
                        for i in range(65536))
        print(f"H{hypothesis}/H{other} relabel XOR in aligned 256MiB: {dict(delta)}")

    wire = [3, 1000, 1000, 111, 222, 333]
    blob = struct.pack("6Q", *wire) + bytes(8 * (11 - 6))
    decoded = struct.unpack("11Q", blob)
    print(f"perf synthetic GROUP: correct_values={wire[3:]}, "
          f"prototype_values={decoded[1:4]}, "
          f"prototype_enabled_running={decoded[9:11]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
