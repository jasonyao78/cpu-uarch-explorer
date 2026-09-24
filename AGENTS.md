# AGENTS.md —— 代理工作指南（本仓约定速查）

> 面向在本仓工作的 AI 代理与人类新成员。只列"必须先知道"的硬约定；细节以链接文件为准。
> 权威来源：需求 `docs/requirements/v0.3.md`，决策 `docs/adr/`，待办 `docs/open-items.md`。

## 构建与测试（本机 macOS-arm64）

```bash
cmake --preset macos-arm64-release && cmake --build --preset macos-arm64-release
ctest --preset macos-arm64-release
.venv/bin/python -m unittest discover -s runner/tests -t .     # runner
.venv/bin/python -m unittest discover -s analysis/tests -t .   # analysis
```

构建目录约定：单一 `build/` 树，`<target-triple>/<profile>` 分层，preset 见 `CMakePresets.json`（ADR-0008）。不要手工 `cmake -B build-x86` 这类平铺目录。

## 运行实验

```bash
.venv/bin/python -m runner.cli plan --experiment configs/experiments/<exp>.json \
  --platform configs/platforms/<platform>.json    # 先预览
.venv/bin/python -m runner.cli run  ...           # 再执行
.venv/bin/python -m analysis.cli report --run data/public/runs/<run目录>
```

## 铁律（违反即返工）

1. **数据纪律**：测量遵守 `docs/methodology/measurement-discipline.md`；违反纪律的数据进 `data/quarantine/`（保留审计），禁止晋升 baseline。绝不编造数值——失败记录用空 metrics + 结构化 `failure`（schema v2 强制）。
2. **数据分层**：`data/public/` 可入库；`data/private/`、`data/restricted/` 永不入库；run 的 `raw/` 样本不入库（SHA256 manifest 锚定，可再生）。设备一律用匿名代号（如 `macbook-m4pro-01`），真实映射在 `data/private/hosts.md`。
3. **注释纪律**：`docs/methodology/comment-discipline.md`——模块锚点、契约 docstring、决策留出处；改代码不改注释视为缺陷。
4. **schema 演进**：`runner/schema/` 扩展字段必须登记到 `runner/schema/README.md`；`additionalProperties=true`，不许破坏旧读者。
5. **git**：monorepo + trunk-based（ADR-0001），小步提交；commit message 格式 `type(scope): summary`；本仓未来转公开，**历史全量可见**——secret/序列号/NDA 内容从第一个 commit 起就不许进来。

## gem5 overlay（third_party/）

- `third_party/gem5` submodule 保持纯净上游，钉 **v25.0.0.1**；一切本地修改只进 `third_party/gem5-d9300-patch/gem5`（唯一事实源，134 文件最小集）。
- 同步：`sh third_party/gem5-d9300-patch/gem5/apply_patchset.sh`（自带基线断言与脏树检测；拒绝时按提示处理，不要 `--force` 类绕过）。
- 构建只在 Xeon 服务器（`michael@10.126.126.128`，`~/cpu-uarch-explorer`）：`scons build/ARM/gem5.opt -j56`，**用系统 scons**；uv python 驱动会导致 gem5py 崩溃（runbook 附2）。macOS 不做 gem5 构建平台（elf.h 阻塞）。
- 本机 → 服务器同步用 `rsync -a --delete --exclude 'build/' --exclude '.DS_Store'`（`--delete` 必须带，否则本机删除的文件在服务器残留）。
- 增量树加文件前先想"它相对基线 v25.0.0.1 的 delta 是什么"；纯旧版携带文件不许进来（普查方法见 `docs/gem5-d9300-intake.md`）。

## 当前阶段（2026-09-25）

M4 Pro 最小骨架已闭环（probe → JSON → 报告）。主线：探针域扩展（core/branch/TLB）与 Xeon 平台接入。gem5 建模后置——校准闭环的启动条件是探针套件齐备 + D9300 实机入册（OI-6）。
