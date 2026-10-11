# Q-D K链上板前软件出口

## 本次任务的目的（给人类看）

在 `docs/design/2026-10-11-tlb-walk-parallel.md` 冻结协议下完成K链作用域测量。本文仅软件/构建/独占证据，不代替手机结果。

- r2 `codex/sm8650-tlb-hierarchy-r2`；源 `0bda583`，consumer/build `757bb46`；实际launch另记manifest。主树/原m0b未修改，远端暂不处理。
- 真实native计划33cell/99窗，16图族实际指针遍历/闭环/offset/置换通过；C++与Python独立规范置换一致。
- NDK27.2/API34，两次构建SHA256相同：0038f7f17769532cf5f9a5abae3b5ebbd88d82a56758b4fbb45736fc1415c7d1。四个实际ELF核由Capstone逐指令解码，loop恰K LDR + SUBS + B.NE，各LDR读回自身寄存器，无spill。证据 `docs/reviews/evidence/2026-10-11-tlb-walk-parallel/{build,plan,code-audit}.json` / `decode.py`。
- 消费者8128高低共变缺口由真实生产形态反例RED→GREEN闭合；same-observation Σ比、M=0命名、负相减保留、background失败不救门。
- 实际producer计划/graph→registered driver→writer→raw consumer成功5进程/495窗（仅外部PMU模拟）。21类重哈希反例拒绝；首bad-K只执行1进程；人为绕过audit则该测试RED。路径 `tools/diagnostic/tests/test_tlb_parallel_{producer,analysis,raw}.py`。
- fresh全量 `.venv/bin/python -m unittest discover -s tools/diagnostic/tests`：281/281，111.560s，完整本地日志 `/tmp/tlb-parallel-full-regression.log`。formal runner203/analysis250/CTest21是此前未改路径的已验证基线，本次不冒称fresh。
- 独占只读检查：1个online target，active probes空，unfinished journals0；driver每块重复环境与身份门，不写环境。macOS只证明图/计划/GROUP纯解码，实际Linux PMU仍由本次有限块验证。

不新增拟合/容量推断，作用域不合格输出not-qualified；5进程全部495窗保存，即使门不通过也不改阈值重跑救门。
