# 2026-10-07 PA 修复回执复核证据

输入：r2 dbd9831、m0b4655dd3、main9093f4a；完整SHA及文件摘要见manifest.json。本目录只含软件评审证据，不含新的设备测量。

| 文件 | 内容 |
|---|---|
| results.json / diagnostics.log | H身份已修及残差身份反例；真实planner六个高N拒绝；真实_run_case一致域、混域及非法审计；生产收集器16项配额/N-set计数/访问前缀/filler/跨界布局；旧51runs/295records重放；main图表组合24项 |
| analysis.log / runner.log | m0b155/187回归输出 |
| build-ctest.log | macOS release配置、构建与CTest19项输出，exit0 |
| ndk-syntax.log | Android arm64 API29两源码语法检查，exit0且无输出；未链接或部署 |
| manifest.json | 输入提交、成功退出码、诊断含义、文件SHA256 |

**边界**：合成stdout/计数、执行器、数值VA均标为SYNTHETIC。C++仅编译提取的生产选址函数，未解引用指针或调用PMU。N-set访问前缀按生产循环边界在整数地址上推演。归档数据来自data/public/runs；旧14条pilot缺字段不回填。本轮无adb/手机探针执行。

复现脚本使用 `--tree` 指定m0b、`--main-tree` 指定图表源，命令见评审§7。旧重放只删除新增且全None的identity，比较其余AnalysisResult和cohort；不是完整输出逐字比较。脚本exit0表示诊断完成，不表示评审通过。

软件检查在m0b工作树执行：

```bash
/Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python -m unittest discover -s analysis/tests -t .
/Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python -m unittest discover -s runner/tests -t .
cmake --preset macos-arm64-release
cmake --build --preset macos-arm64-release
ctest --preset macos-arm64-release
/Users/michaelyao/Library/Android/sdk/ndk/27.2.12479018/toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android29-clang++ \
  -std=c++17 -fsyntax-only -DCPU_UARCH_HAVE_LINUX_PERF=1 \
  -I probes/common -I probes/platform/linux \
  probes/cache-mem/ptr_chase.cpp probes/tests/perf_window_golden.cpp
```
