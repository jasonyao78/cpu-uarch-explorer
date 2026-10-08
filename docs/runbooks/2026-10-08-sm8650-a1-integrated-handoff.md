# SM8650 A1 集成基线交接（2026-10-08）

## 本次任务的目的（给人类看）

把已收口的软件消费链交给上板 Agent：从 r2 集成基线交叉编译 Android arm64 探针、验证目标路径、生成独立标定冻结工件，再执行正式三层矩阵。本文不是已执行的设备验收；本次软件负责人没有连接手机或运行 adb/perf。

## 基线与责任

集成分支 `codex/sm8650-tlb-hierarchy-r2`，工作区 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/`。代码整合提交 `95987b9`（m0b `a98c598` 合入）及 `3c95aeb`（main `6062e20` 的已提交图表/文档修复同步）。本交接及任务书 v1.9 的提交位于其后；上板前记录实际 r2 HEAD，并要求 tracked 工作树干净。

软件实现/集成验收已由当前 Agent 完成；原上板 Agent 负责以下设备链。无需再让原行动方重复修本轮软件。m0b 开发使命结束，仍保留分支/worktree供并行会话处理已有数据与进程依赖；不要在旧 m0b 上继续新增正式 A1 采样。main 工作区的并行改动保留，r2 尚未反向合入 main；远程暂不操作。

## 上板行动顺序

1. **基线和二进制**：记录 r2 SHA，使用 Android NDK 交叉编译 aarch64 完整可执行探针（不仅 syntax-only）。核对 `configs/platforms/redmi-k70pro-01.json` 的 `probes.ptr_chase.local/remote` 与实际产物，记录构建命令、NDK/API、源码 SHA、二进制 SHA。当前 Android 专用 CMake preset 缺口仍在 `docs/open-items.md`，由本设备构建任务选择并登记标准路径；不要将 macOS CTest 当 Android 运行证据。
2. **部署与前置验证**：依照 `docs/runbooks/2026-10-01-sm8650-tlb-r2-preboard.md`（历史执行参考，不继承为本次已通过），检查 adb/root、实际 X4/MIDR/页大小、事件权限、charging-thermal、二进制两端摘要。验证 Linux guarded VMA、PerfWindow 和新几何全域/隔离实际激励；失败命名记录，不晋升 baseline。绝不将合成传输的 1280 次调用称手机进程。
3. **先预览专用标定**：用真实 runner 的 `plan` 分别展开 `configs/experiments/ptr-chase-sm8650-x4-tlb-a1-calibration-floor.json` 和 `...-calibration-scatter.json`，确认各 1 case/10 reps、W0 与 W8/scatter1、scope−1、CPU7。所有正式/标定 run 显式选择 `--environment-profile charging-thermal`。保持同一二进制/clean source/regime；块前后锚点遵守任务书 §5.3–5.4。
4. **标定并冻结**：运行上述两配置，保存 run目录、records/manifest/artifacts、raw 字节。运行下面 `freeze` 命令。退出2是 STOP，只保存审计；退出1是输入错误；两者均不得启动正式矩阵。退出0后记录工件摘要，停止修改配置/代码/二进制/regime。新条件需新标定和新文件，不覆盖旧工件。
5. **正式 A1**：依次预览/执行 `...-a1-l1-main.json`、`...-a1-l2-repro.json`、`...-a1-l3-target.json`，成功记录数应为48/48/32，每 case10进程。角色、覆盖、统计、实际 hi 和跨块谱系由最终入口强制；失败/缺点不可手工补 ID/改 realized/删除后继续宣称整矩阵合格。
6. **裁定与交回**：运行 `adjudicate`，提交命名拒绝或完整结果、case_audit、标定工件与谱系、环境/锚点记录。H* 多候选或 none-supported 是允许的科学终态；不得为选出唯一候选重调冻结阈值。A3 仍按已登记条件后置。

## 文件入口

在 r2 根目录；Python 可用现有 `/Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python`，以下环境变量只代表实际路径，由执行方填写。

```bash
python -m analysis.sm8650_tlb_a1_cli freeze \
  --floor-run <floor-run目录> --scatter-run <scatter-run目录> \
  --out <新的frozen.json>

python -m analysis.sm8650_tlb_a1_cli adjudicate \
  --run <L1-run目录> --run <L2-run目录> --run <L3-run目录> \
  --frozen-file <frozen.json> --out <adjudication.json>
```

规则与部件路径：`docs/tasks/2026-09-30-sm8650-tlb-hierarchy-r2.md` §5.5；`analysis/sm8650_tlb_a1_contract.py`、`analysis/sm8650_tlb_a1_freeze.py`、`analysis/sm8650_tlb_a1_cli.py`；schema 登记在 `runner/schema/README.md`。软件验收与证据见 `docs/reviews/2026-10-08-a1-software-exit-and-integration.md`。

raw 按既有数据纪律留存，manifest 锚定、raw 不入库；`data/private/` 与 `data/restricted/` 永不入库。冻结工件包含本机绝对路径，分享/归档前按数据层处理；移动标定目录须重新生成并审计新工件，不手改旧工件。
