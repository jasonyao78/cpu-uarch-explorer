# SM8650 A1 集成基线交接 v2（2026-10-08）

## 本次任务的目的（给人类看）

在已集成的 r2 上，先证明修复后的探针能产生合格几何，再独立标定冻结，最后采集正式三层矩阵。旧 pilot 已有设备路径和对照信号，不能直接当本次标定或正式结论。**下一步是新二进制的几何资格冒烟，不是立即跑1280进程。**

依据 `docs/reviews/2026-10-08-a1-geometry-and-pilot-audit.md`。软件负责人本轮只做宿主验证和旧数据只读审计，没有连接手机或运行 adb/perf；目标手机执行继续由原上板 Agent 完成。

## 本版更新了什么

1. 吸收旧 pilot 的设备路径、PMU窗口与正/负控信号，同时登记失败和未完成run。
2. 更正旧domain标志、跨二进制锚点与空窗dirty source的证据口径；旧数据不回填、不晋升正式标定。
3. `probes/common/tlb_set_layout.h` 实现预约内对齐，解除任意mmap基址导致池跨256MiB窗口的问题；保留完整actual realized和purity硬门。
4. 增加 `configs/experiments/ptr-chase-sm8650-x4-tlb-a1-geometry-smoke.json` 的12cases/24进程资格阶段，通过后才专用标定。
5. 明确冻结工件、48/48/32的含义及启动/停止条件；软件自验和真机待验分别陈述。

## 基线与责任

执行工作区 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2/`，分支 `codex/sm8650-tlb-hierarchy-r2`。已集成 m0b `a98c598`（merge `95987b9`）与 main 已提交 `6062e20`（merge `3c95aeb`）。本轮几何修复提交为 **`49da3e7`**，交接/证据提交位于其后；**记录实际r2 HEAD，要求tracked树干净，按新源码完整重编。旧36aa9228…二进制不包含此次几何修复。**

m0b开发使命结束，只保留既有数据/并行依赖；不在旧m0b新增正式A1。r2尚未反向合入main，远程暂不操作。

上板Agent可执行预注册配置及 `analysis/sm8650_tlb_a1_cli.py` 冻结/裁定程序；不得自行选择阈值、扩参、放宽门或改实现。程序STOP/输入错误回传软件负责人，科学解释由分析侧复核。旧 `docs/runbooks/2026-10-07-sm8650-tlb-pilot-kickoff.md` 的“阈值冻结不属执行方”指人为决策，本交接明确授权运行既定程序。

## 旧pilot：可引用事实与不可继承的资格

原数据留在 `/Users/michaelyao/workspace/cpu-uarch-explorer-tlb-r2-m0b/data/public/runs/`，派生审计见 `docs/reviews/evidence/2026-10-08-a1-geometry/pilot-audit.json`。

- 成功选取9条记录/90个进程观测；另有 `20261008T081255Z-...-g03-empty` 的1条失败记录/10份raw工件，及 `20261008T082019Z-...-g03-noconflict` 的未完成run（records空、raw子目录、无manifest）。100份现存raw工件摘要匹配，不把“成功选取9/9”写成所有尝试全成功。
- 50个tlb-set样本均为multi-region。旧5条record的domain_consistent=false把域内VA变化也算入，不是实际混域的证明；当前 `runner/engine.py` 已按域字段判断，并保留逐进程审计。
- 14/50样本purity=0，检查对象是整个区域池，不能直接推断每条实际目标链都跨界。但 `analysis/sm8650_tlb_a1_contract.py` 要求所有scope和所有样本purity=1，旧“仅标注/仅降级H3/H4”不适用。
- 前锚点binary=1e03a658…，后锚点=36aa9228…；−0.6%/−0.8%只作描述，不算同一binary夹块验收。成功空窗source=b0f287f、dirty=true；后续noconflict才是clean6f433e3。
- 空窗与scatter的L2 refill中位为0，集中选址对照为每轮8.0/6.0；可引用对照响应，不能命名8-way/6-way或确定H模型。r10/r40不是本次r20专用标定。
- 当前freeze对旧run返回 `calibration floor identity mismatch`，旧realized另缺必要descriptor；不能补ID、改flag或裁剪样本来适配。

## 设备执行顺序与硬门

### 1. 新二进制与当前环境

记录r2 SHA，用Android NDK交叉编译aarch64**完整可执行探针**。记录NDK/API、完整构建命令、源码SHA、完整binary SHA256；核对 `configs/platforms/redmi-k70pro-01.json` 的local/remote产物与设备端摘要。Android专用preset缺口沿 `docs/open-items.md` 的SMOKE-20261001；构建命令与 `build/<target>/<profile>/` 标准路径由设备构建方登记。

按 `docs/runbooks/2026-10-01-sm8650-tlb-r2-preboard.md` 重读adb/root、X4/MIDR、4KiB页、事件权限及charging-thermal；历史通过不能继承。公共回执仅用redmi-k70pro-01，不写真实设备标识。验证Linux守卫VMA/PerfWindow相应路径；失败留命名记录，macOS CTest不能代替。

### 2. 几何资格冒烟：12cases / 24进程

配置 `configs/experiments/ptr-chase-sm8650-x4-tlb-a1-geometry-smoke.json`：H{1,2,3,4}×scope{-1,0,1}×W12，target7、seed42、r20，每case2进程。只用于设备几何资格，不输入freeze或正式A1。

```bash
PY=/Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python
PLAT=configs/platforms/redmi-k70pro-01.json
GEOM=configs/experiments/ptr-chase-sm8650-x4-tlb-a1-geometry-smoke.json
"$PY" -m runner.cli plan --experiment "$GEOM" --platform "$PLAT" --environment-profile charging-thermal
# 确认12cases、各2reps及CPU7后执行；allow-mutation只给run。
"$PY" -m runner.cli run --experiment "$GEOM" --platform "$PLAT" --environment-profile charging-thermal --allow-mutation
```

将下面占位路径替换为实际run目录，执行只读核验。复用正式逐进程几何/统计/谱系检查，按冒烟plan的2reps核验，不作H判定：

```bash
"$PY" - <geometry-run目录> <<'PY'
import sys
from pathlib import Path
from analysis.sm8650_tlb import TlbError
from analysis.sm8650_tlb_a1_contract import canonical, expected_cases, validate_record
from analysis.sm8650_tlb_a1_freeze import load_audited_run, record_provenance
cases = expected_cases('configs/experiments/ptr-chase-sm8650-x4-tlb-a1-geometry-smoke.json', 'geometry')
expected = {c.key: c for c in cases}
records, _ = load_audited_run(Path(sys.argv[1]))
seen, ids, refs, sources = set(), set(), set(), set()
if len(expected) != 12 or any(c.repetitions != 2 for c in cases):
    raise TlbError('geometry: unexpected smoke plan')
for r in records:
    key = (r.get('experiment_id'), canonical(r.get('params')), canonical(r.get('environment', {}).get('control')))
    if key not in expected or key in seen or not r.get('run_id') or r['run_id'] in ids:
        raise TlbError('geometry: unknown/duplicate case or record')
    metrics = validate_record(r, expected[key])
    raw = {o['raw_sample_ref'] for o in metrics['pmu.l2d_tlb_refill.count']['observations']}
    if refs & raw:
        raise TlbError('geometry: repeated process across cases')
    seen.add(key); ids.add(r['run_id']); refs.update(raw)
    sources.add(canonical(record_provenance(r)))
if seen != set(expected) or len(refs) != 24 or len(sources) != 1:
    raise TlbError('geometry: incomplete coverage or provenance/regime drift')
print('PASS: 12 cases / 24 processes; geometry and qualification only')
PY
```

**通过条件**：12/12记录ok、ID/完整条件与plan一致、每case2个有效完整观测，逐进程全域配额或指定隔离槽位正确、purity=1、高字段符合合同、无fallback/真实混域，source/binary/regime一致且环境合格。任一错误停块，不筛掉不纯进程继续宣布通过；失败/未完成run也进流水账。

### 3. 同一新binary的锚点与专用标定

依次plan→run `configs/experiments/ptr-chase-sm8650-x4-tlb-anchor.json` 的前锚点、`configs/experiments/ptr-chase-sm8650-x4-tlb-a1-calibration-floor.json`（W0）、`configs/experiments/ptr-chase-sm8650-x4-tlb-a1-calibration-scatter.json`（W8/scatter1）及后锚点。两标定各1case/10reps、r20、scope−1、CPU7，均显式 `--environment-profile charging-thermal`，run才带 `--allow-mutation`。

保持同一clean source/binary/regime，锚点沿任务书§5.3–5.4调查门；标定每进程也过完整realized/purity门。保留records/manifest/artifacts和raw；旧pilot不代入。每正式块前置标定复测及锚点仍沿任务书；复测与初始冻结输入分别归档，不混入正式曲线。

### 4. “冻结成功”的精确定义

`analysis/sm8650_tlb_a1_freeze.py` 核验专用输入身份、样本资格及同源环境，再由 `analysis/sm8650_tlb_a1.py::freeze_thresholds` 按预注册网格/STOP规则选值；不是人工看中位数填写2.0或3.0。

```bash
"$PY" -m analysis.sm8650_tlb_a1_cli freeze \
  --floor-run <新的floor-run目录> --scatter-run <新的scatter-run目录> \
  --out <新的frozen.json>
```

- 退出0并生成完整 `frozen=true` 工件：冻结资格通过，记录工件摘要，才可继续第5步。
- 退出2：规则判STOP，保存审计并停止；退出1：输入/谱系等错误，停止回传。
- 工件锚定代码/配置、标定文件、binary/source/regime，新布局头也在CODE_PATHS。条件变化须新标定/新工件，不覆盖旧文件或手改阈值。

### 5. “正式48／48／32矩阵”的精确定义

矩阵是实验条件组合，不是48/48/32个CPU单元或TLB容量：

| 层 | 精确配置路径 | 条件组合 | cases | 手机进程 |
|---|---|---|---:|---:|
| L1主判定 | `configs/experiments/ptr-chase-sm8650-x4-tlb-a1-l1-main.json` | 4H×3scope×4W，target7/seed42 | 48 | 480 |
| L2独立顺序复现 | `configs/experiments/ptr-chase-sm8650-x4-tlb-a1-l2-repro.json` | 同L1，seed1337 | 48 | 480 |
| L3跨target附加一致性 | `configs/experiments/ptr-chase-sm8650-x4-tlb-a1-l3-target.json` | 4H×4target×2W，scope−1/seed42 | 32 | 320 |
| 合计 | 三份正式配置 | 每case10个独立进程 | **128** | **1280** |

H是候选地址索引假设，scope是全域或隔离区域，W是每轮目标页数；L1/L2/L3是证据层，不是三级TLB。标定和几何冒烟在此数量之外。L3两点只查附加形态，onset证据来自L1/L2四点网格。

通过第2–4步后依次plan→run三配置，每块核验后才进入下一块；失败停止，不用无退出检查的循环连续跑完。完整身份/覆盖/实际hi/谱系由最终入口强制；不补ID、改realized或删除失败点后继续宣称整矩阵合格。

### 6. 正式裁定与回传

```bash
"$PY" -m analysis.sm8650_tlb_a1_cli adjudicate \
  --run <L1-run目录> --run <L2-run目录> --run <L3-run目录> \
  --frozen-file <frozen.json> --out <adjudication.json>
```

交回完整结果或命名拒绝、case_audit、冻结工件、锚点及环境/构建谱系、全部成功/失败/未完成尝试清单。unique、equivalent-on-test-domain、none-supported均允许，不为唯一H*重调阈值。A3按 `docs/open-items.md` 原触发条件后置。

## 参考与数据纪律

规则：`docs/tasks/2026-09-30-sm8650-tlb-hierarchy-r2.md` §5.5（v1.9.1）。组件：`probes/common/tlb_set_layout.h`、`probes/common/tlb_set_collect.h`、`analysis/sm8650_tlb_a1_contract.py`、`analysis/sm8650_tlb_a1_freeze.py`、`analysis/sm8650_tlb_a1_cli.py`；schema见 `runner/schema/README.md`，本轮不新增record字段。

历史软件验收：`docs/reviews/2026-10-08-a1-software-exit-and-integration.md`；本轮审计：`docs/reviews/2026-10-08-a1-geometry-and-pilot-audit.md`。raw不入库，manifest锚定，private/restricted永不入库。冻结工件含本机绝对路径，分享前按数据层处理；移动输入目录须重新审计生成工件，不手改旧文件。旧m0b数据由原采数方归档，不由软件负责人移动或代提交。
