# 2026-10-07 MB-06 / OI-13 / Phase A 复核证据

输入：r2 d086173，m0b 0b8c8b1，main 9093f4a。完整 SHA 在 results.json 的 tree_head/main_head 与 manifest.json 中。

本目录是**软件评审证据**。results.json 中的 fabricated PMU values、stdout 和数值 VA 均为 SYNTHETIC fixtures。地址选择 harness 使用生产函数，仅做整数选址，不解引用地址、不执行 PerfWindow/PMU。pilot_record_contract 与 legacy_replay 只读仓内已归档公共记录。**本轮未执行 adb 或目标探针。**

| 文件 | 内容 |
|---|---|
| results.json / diagnostics.log | 分组/二次聚合/descriptor 反例；生产选址函数16项；51 runs/295 records规范化重放；14 pilot records契约字段检查；main组合24项、MB-03四项、MB-07缺口与完整图表5文件差分 |
| analysis.log | m0b analysis 153/153 |
| runner.log | m0b runner 182/182 |
| build.log / ctest.log | m0b macOS release构建成功，CTest19/19；不覆盖Linux专属执行分支 |
| main-analysis.log | main analysis170/170 |
| ndk-syntax.log | arm64 API29两源码语法检查，成功时无输出；退出0记录在manifest中 |
| manifest.json | 文件SHA256、输入提交、命令及成功退出码 |

运行位置 m0b：

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

main的analysis回归在main工作树运行同一unittest命令。诊断脚本的复现命令见正式评审§4。main+m0b“组合”指在独立Python进程中以m0b的analysis模块加载main图表及其真实测试，不声称Git已合并。

**判读**：诊断脚本退出0表示诊断完成，不表示送审通过。重放的规范化仅删除新增且四字段均None的group.identity；其余AnalysisResult及cohort均比较。不要将这项归一化结构比较写成完整输出逐字一致。
