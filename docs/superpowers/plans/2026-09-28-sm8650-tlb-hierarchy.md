# SM8650 Cortex-X4 TLB 层级探测实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 按 superpowers:executing-plans
> 或 subagent-driven-development 逐任务执行；步骤用 checkbox（`- [ ]`）
> 跟踪。规范基线 = 任务书 v4.1（commit `55c3a73`，
> `docs/tasks/2026-09-28-sm8650-tlb-hierarchy.md`）——本计划不得与之冲
> 突；冲突一律以任务书为准并回写计划。

**Goal:** 按任务书 v4.1 完成 SM8650 CPU7 的 TLB 层级探测：Q1（`0x05`
第一转折）/ Q2a（`0x34` walk-onset）/ Q3（关联曲线，默认
`MODEL_UNIDENTIFIABLE`）/ Q4（THP cohort 对照），全部按预注册规则裁
定并如实结案。

**Architecture:** 唯一代码增量 = 探针 `vma_base` 字段 + 事件注册表 +
`analysis/sm8650_tlb.py` 规则引擎 + 致密点生成器 + 阶段化实验配置；设
备采集全部复用现有 `ptr_chase` + runner + controlled-baseline。规则判
定全部落在入库分析器（TDD），不做任何 ad-hoc 看图判定。

**Tech Stack:** C++17/CMake（探针）、Python unittest（runner/analysis）、
JSON 配置、Arm TRM（Issue 05）+ `cortex-x4.json`（事件语义，已冻结哈
希）、AArch64-Explore（方法学参照，禁数值移植）。

**执行顺序约束：** M1–M2 全在主机完成（不碰设备）；M3 起按序上设备；
任何 Gate 失败按任务书终态处置，**不绕过、不改判据**。

---

## 里程碑 M1：Specification Closure 落地（纯主机）

### Task 1: 探针 `vma_base` 输出字段（TDD）

**Files:**
- Modify: `probes/cache-mem/ptr_chase.cpp`（输出格式段）
- Modify: `runner/adapters/ptr_chase.py`（parse_output + docstring ABI 块）
- Modify: `runner/schema/README.md`（字段登记）
- Modify: `runner/tests/test_ptr_chase_contract.py`

- [ ] **Step 1: 写失败测试**——在 `test_ptr_chase_contract.py` 增加：

```python
    def test_vma_base_is_recorded(self):
        argv = self.adapter.build_argv(
            {"buffer_kb": 64, "stride": 64, "loads": 8000, "warmup": 1000})
        proc = self._run(argv)
        self.assertEqual(proc.returncode, 0)
        metric = self.adapter.parse_output(proc.stdout, proc.stderr)[0]
        self.assertIn("vma_base", metric)
        self.assertRegex(metric["vma_base"], r"^0x[0-9a-f]+$")
```

另加合成输出用例：`latency_ns=1 vma_base=0x7f12ab` 解析进 metric；`vma_base=xyz`（非 hex）抛 `ParseError`。

- [ ] **Step 2: 运行确认失败**——`.venv/bin/python -m unittest runner.tests.test_ptr_chase_contract -v 2>&1 | grep vma`；预期 `KeyError: 'vma_base'` 或字段缺失。

- [ ] **Step 3: 探针输出字段**——`ptr_chase.cpp` 在现有 printf 的 `seed=%llu` 前插入 `vma_base=%p `（对应实参 `static_cast<void*>(buf)`）；头部注释"输出"清单补 `vma_base`。adapter 在 `seed` 处理旁按字符串解析 `vma_base`（正则 `^0x[0-9a-f]+$`，不转 int），写入所有 metric。schema README 登记表行：`vma_base | string (hex) | 建链缓冲区起始 VA（ASLR，布局观测，路线 A） | 2026-09-28`。

- [ ] **Step 4: 验证绿**——重建 `cmake --build --preset macos-arm64-release`，跑新测试 + `ctest --preset macos-arm64-release`（17→18）+ runner 全套（138→140）。

- [ ] **Step 5: 提交**——`git commit -m "feat(ptr-chase): record VMA base for layout observation"`。

### Task 2: 事件注册表 `configs/pmu-event-registry.json`（TDD）

**Files:**
- Create: `configs/pmu-event-registry.json`
- Create: `runner/tests/test_pmu_registry.py`（结构守卫）

- [ ] **Step 1: 写失败测试**——断言注册表存在、JSON 数组、每条含 `{type, config, name, midr, source_doc, source_revision, positive_control_run, outcome, review_ref, validity_scope, qualification}` 且 `qualification ∈ {"candidate","qualified"}`；`0x05`/`0x34`/`0x8144` 为 `qualified` 且 midr=`0x410fd821`。

- [ ] **Step 2: 运行确认失败**（文件不存在）。

- [ ] **Step 3: 写注册表**——初始三条 QUALIFIED 记录：`0x05`/`0x34`（positive_control_run=`20260927T182613Z`）、`0x8144`（P0″ runs）；source_doc=`102484_0002_05_en`（TRM 文本列）+ `cortex-x4.json@sha256:c11c4ee0f6ad6b61`；CANDIDATE 记录留空数组位（Gate 1 时追加）。

- [ ] **Step 4: 验证绿**——`.venv/bin/python -m unittest runner.tests.test_pmu_registry -v`。

- [ ] **Step 5: 提交**——`git commit -m "config(sm8650): register PMU event qualifications"`。

### Task 3: 锚点 + 正控 + 粗扫三个实验配置（TDD：plan 守卫先行）

**Files:**
- Create: `configs/experiments/ptr-chase-sm8650-x4-tlb-anchor.json`
- Create: `configs/experiments/ptr-chase-sm8650-x4-tlb-ctrl.json`
- Create: `configs/experiments/ptr-chase-sm8650-x4-tlb-coarse.json`
- Modify: `runner/tests/test_plan.py`（protocol/case-count 守卫）

- [ ] **Step 1: 守卫加行（失败测试）**——`expected_case_counts` 增：`ptr-chase-sm8650-x4-tlb-anchor.json: 2`、`ptr-chase-sm8650-x4-tlb-ctrl.json: 2`、`ptr-chase-sm8650-x4-tlb-coarse.json: 26`；protocol_12_prefixes 增 `ptr-chase-sm8650-x4-tlb-`。**另加存在性断言**（注册项必须真实存在，防悬空）与**参数钉**（锚点/粗扫的 buffer/seed/事件组断言）——评审实证只有 case 数兜不住 buffer 列表错改。运行确认失败（配置不存在）。

- [ ] **Step 2: anchor 配置**——clone P0″ 结构：G0 事件组（cycles `0x11`、mem_access_rd `0x66`、l1d_tlb_refill `0x05`、dtlb_walk `0x34`）、sweep buffer `["512KiB","3072KiB"]`、`base_pages=1`、`loads_per_slot=8`、`min_loads=4096`、`warmup_passes=2`、`repetitions=10`、seed 固定参数 `seed=42`（declared default，不 sweep）、controls `["x4-prime"]`。

- [ ] **Step 3: ctrl 配置**——同事件组（G0），sweep buffer `["512KiB","16MiB"]`（128/4096 页 floor/scale 锚点），其余同 anchor。备注：本配置即 Gate 1 的 floor/scale 锚点载体，新事件按 §5.1 顺序逐组加入（Gate 1 时改配置并重跑）。

- [ ] **Step 4: coarse 配置（Phase A）**——G0 事件组；sweep buffer 由页数映射（pages×4KiB）：`["128KiB","256KiB","384KiB","512KiB","768KiB","1MiB","1536KiB","2MiB","3MiB","4MiB","8MiB","16MiB","32MiB"]` = 32..8192 页 13 档 + seed 叉积 `[42, 7]` = 26 case；`base_pages=1`、`loads_per_slot=8`、`min_loads=4096`、`repetitions=10`。

- [ ] **Step 5: plan 预览验证**——三个配置分别 `runner.cli plan`：anchor=2 case（512/3072 KiB）、ctrl=2 case（512 KiB/16 MiB）、coarse=26 case（13 档 × 2 seed）；与 Step 1 守卫断言一致后跑 `runner.tests.test_plan` 全绿。

- [ ] **Step 6: 提交**——`git commit -m "config(sm8650): stage TLB anchor/control/coarse experiments"`。

### Task 4: 分析器骨架与契约（TDD）

**Files:**
- Create: `analysis/sm8650_tlb.py`
- Create: `analysis/tests/test_sm8650_tlb.py`

- [ ] **Step 1: 写首批失败测试**（合成记录仿 `test_sm8650_x4_p0prime` 的 `_record` 模式，含 `vma_base` 字段）：
  1. 正控点（128/4096 页）**不被误报为 knee**（§6.2.2 三条件不全满足时无候选）；
  2. `0x05` 值 >1000/1k 时 density 原值输出（不截断）；
  3. 未注册事件（注册表无记录）→ 该事件相关结论输出 `SEMANTICS_UNVERIFIED`，但样本仍入表；
  4. `running != enabled` 样本进 rejected；
  5. 全失败 run 进 rejected 不抛错。

- [ ] **Step 2: 运行确认失败**（模块不存在）。

- [ ] **Step 3: 实现骨架**——复用 `sm8650_x4_p0prime.py` 的校验链（编码/running/seed/sample_index/backing/全失败 run）；`_REQUIRED_METRICS` = latency + G0 四个 pmu 指标；`event density` 计算；`TlbError(ValueError)`；`analyze_records(records, run_label) -> AnalysisResult(groups, rejected)`；注册表加载器 `load_registry(path)`（含 qualification 查询）。

- [ ] **Step 4: 验证绿**——`.venv/bin/python -m unittest analysis.tests.test_sm8650_tlb -v` + analysis 全套（21→26）。

- [ ] **Step 5: 提交**——`git commit -m "feat(analysis): scaffold TLB analyzer with registry gating"`。

---

## 里程碑 M2：规则引擎（knee/onset/锚点/生成器，纯主机）

### Task 5: knee/onset 检测与终态（TDD）

**Files:**
- Modify: `analysis/sm8650_tlb.py`
- Modify: `analysis/tests/test_sm8650_tlb.py`

- [ ] **Step 1: 失败测试**——合成曲线用例：§6.2.1 页序下的 ①单膝点（128→192 满足三条件）；②双膝点；③无膝点（连续上升）→ `RIGHT_CENSORED`；④`R_0x05(32)=120/1k` → `LEFT_CENSORED`（优先于 knee）；⑤walk-onset 满足 §6.2.3 三条件；⑥onset 仅在单点满足无持续 → 不报 onset；⑦边界点（8192 未满足）→ `RIGHT_CENSORED`。

- [ ] **Step 2-4: 实现并转绿**——§6.2.2/6.2.3/6.2.8-1 的确定性实现（输入为 (buffer, R_0x05, R_0x34, cyc/load) 序列）。**另含双峰标记补齐**（任务书 §9.2 的复用契约）：移植 p0prime 的 `_is_bimodal` 规则（排序相邻比 ≥4 且两侧各 ≥2），目标字段钉为 `l1d_tlb_refill_per_1k`（knee 判据的消费字段；逐进程布局/着色方差的主要暴露面），测试用例：清晰双峰组 → bimodal=True、干净组 → False。

- [ ] **Step 5: 提交**——`git commit -m "feat(analysis): detect TLB knee and walk onset per frozen rules"`。

### Task 6: 锚点判定与块归组（TDD）

**Files:**
- Modify: `analysis/sm8650_tlb.py`
- Modify: `analysis/tests/test_sm8650_tlb.py`

- [ ] **Step 1: 失败测试**——三块归组（anchor-before + 主体 + anchor-after 按 experiment_id）：①anchor latency 偏差 2% 通过；②偏差 5% → 主体块 `BLOCK_FAILED` 且主体 case 不入判定；③512 KiB R 值落在正控 [p25,p75] 外 → 失败；④3072 KiB 首块只记录不判失（自校准）、第二块与之比较；⑤归组缺 anchor-after → `BLOCK_INCOMPLETE`。

- [ ] **Step 2-4: 实现并转绿**——§6.2.5 判据 + §6.4 归组（experiment_id + manifest 时序）。

- [ ] **Step 5: 提交**——`git commit -m "feat(analysis): validate anchors and group blocks by experiment id"`。

### Task 7: 致密点生成器（TDD）

**Files:**
- Create: `analysis/tlb_dense_gen.py`
- Create: `analysis/tests/test_tlb_dense_gen.py`

- [ ] **Step 1: 失败测试**——①4a：候选 [128,192] → 插入 144,160,176 + 64（去重升序，向下取整）；②4b：onset (2048,4096) 独立生成；③Q1 无候选 + Q2a 有 onset → 仅 4b 输出；④并列候选按 p_i 升序取前 3；⑤区间 >3 时按相对增量裁剪；⑥输出配置 JSON 含 `generator: {input_run_sha256, rules_sha256, output_sha256}` 三字段；⑦重合插入点按 §6.2.8-3 计额。

- [ ] **Step 2-4: 实现并转绿**——`emit_dense_config(coarse_result, rules_version) -> dict`（确定性，输出即可写 `ptr-chase-sm8650-x4-tlb-dense.json` 的内容 + plan 预览）。

- [ ] **Step 5: 提交**——`git commit -m "feat(analysis): add deterministic dense-point generator"`。

### Task 8: cohort 与 Q3/Q4 规则（TDD）

**Files:**
- Modify: `analysis/sm8650_tlb.py`
- Modify: `analysis/tests/test_sm8650_tlb.py`

- [ ] **Step 1: 失败测试**——①cohort 5 个有效样本 → 比较级 median；②4 个 → 描述级无 median；③2 个 → `INSUFFICIENT_COHORT`；④跨 seed 同制度合并、异制度分列；⑤G3 缺失时 Q3 输出 `MODEL_UNIDENTIFIABLE` 且无成本值；⑥混合不并入 thp；⑦40/point·policy 进程额度计数（失败计额）。

- [ ] **Step 2-4: 实现并转绿**——§7 Phase D 分级 + 转化表 + Q3 默认终态。

- [ ] **Step 5: 提交**——`git commit -m "feat(analysis): add THP cohort rules and Q3 default outcome"`。

### Task 9: M1–M2 全量验证（门禁）

- [ ] `ctest --preset macos-arm64-release && ctest --preset macos-arm64-ubsan`
- [ ] `.venv/bin/python -m unittest discover -s runner/tests -t .`
- [ ] `.venv/bin/python -m unittest discover -s analysis/tests -t .`
- [ ] `git diff --check && git status --short`
- [ ] 记录测试计数（预期：CTest 18、runner ~142、analysis ~40）写入 M2 完成注记。
- [ ] **⑮ 映射核对**：任务书 §9.3 测试⑮（plan 展开契约）逐项对到落点——锚点 case/顺序=Task 3 守卫、块归组=Task 6、计数单位与裁剪=Task 13 守卫、事件资格两级=Task 2、失败计额=Task 8⑦、cohort 下限=Task 8、vma_base=Task 1——全部有归属后 M2 方可关闭。

---

## 里程碑 M3：设备 Gate 0/1（首次上设备）

### Task 10: Gate 0 契约复验 + 交叉构建部署

- [ ] 按开机序列准备设备（重启四触发判定 → 静置 → quiet-state 门禁 → 5–10 min 限额稳定性观察）。
- [ ] Xeon 交叉构建含 `vma_base` 的探针（专用干净目录），SHA-256 三方一致后 adb 部署（manifest 锚定）。
- [ ] 跑 `tlb-ctrl`（G0）：确认 8 项契约（任务书 §4）：编码/running==enabled/loads 自洽/端点审计/恢复 walt/`vma_base` 在 records 中。
- [ ] 低成本锚点（512 KiB 单进程）对照 short-base 组。
- [ ] 提交 run 数据（schema 校验后）：`git commit -m "data(sm8650): record TLB Gate 0 verification runs"`。

### Task 11: Gate 1 新增事件正控（按 §5.1 顺序）+ §5.3 固定开销扫描

- [ ] ①`0x2d/0x2f`：ctrl 配置加入后重跑（G1 组）；过判据 → 注册表升 QUALIFIED（含 run ID）→ 提交 `data(sm8650): qualify L2 TLB events`。
- [ ] ②`0x8136/0x8128`：G2 组同法；③`0x8138/0x813a`：G4 组（含 `-T` cohort 对照）同法。任一失败 → 注册 `SEMANTICS_UNVERIFIED`、对应结论降级、不续试新事件。
- [ ] **§5.3 固定开销扫描（正控期间顺带执行）**：512 KiB 与 16 MiB 两点 × 8/64/256 ring passes × G0 组，逐事件拟合 `C_e(N)=a_e+b_e·N`；`|a_e|/C_e(N)` ≤5% 判定写入正控评审；超阈值事件在后续 Phase 报告标注"含固定开销"。
- [ ] 每步：schema 校验 + 注册表更新 + 提交。

---

## 里程碑 M4–M7：Phase A–D

### Task 12: Phase A 粗扫 + 候选提取

- [ ] 块结构执行：anchor-before → `tlb-coarse` → anchor-after；锚点判据（Task 6 实现的分析器）先行。
- [ ] 块 fail-closed 时按 §6.2.5 处置（查明+重跑占额）。
- [ ] `sm8650_tlb.py` 输出候选区（§6.2.2/6.2.3）；提交 run 数据 + 分析快照：`data(sm8650): record TLB Phase A coarse scan`。

### Task 13: Phase B 致密扫描（含长训练行）

- [ ] `tlb_dense_gen.py` 产出 dense 配置 + 三哈希；plan 预览 + 守卫登记（case 数与 §6.2.7 对齐）。多 seed `refill_ratio` 聚合口径 = 各 seed 最大比值（冻结，见 `analysis/tlb_dense_gen.py` docstring）；`generator` 扩展字段已登记 `runner/schema/README.md`（执行时核对登记行仍在）。
- [ ] 块结构执行主体（短训练）；随后长训练行（≤12 case，timed=slots×512，逐点核算执行量，热中止按 §7 规则整块重试一次）。
- [ ] §6.2.6 稳定条件判定 → Q1/Q2a 终态；提交：`data(sm8650): record TLB Phase B dense scans`。

### Task 14: Phase C 关联曲线（默认终态）

- [ ] G2 先行、G3（含 `0x8144`）对照；跨组锚点可比性检查。
- [ ] 输出关联曲线 + `MODEL_UNIDENTIFIABLE`（除非实施计划补充冻结模型规格——本计划**不含**该规格，故默认不输出成本值）。
- [ ] 提交：`data(sm8650): record TLB Phase C associational runs`。

### Task 15: Phase D THP cohort

- [ ] `tlb-thp` 配置（512/2304/3072 KiB 三点 × `-B`/`-T`）；每（buffer×policy）≤40 进程次（失败计额）；cohort 分级与转化表。
- [ ] `INSUFFICIENT_COHORT` 按预注册终态，不追加尝试。
- [ ] 提交：`data(sm8650): record TLB Phase D THP cohorts`。

---

## 里程碑 M8：报告、评审与退役

### Task 16: 评审文档与收尾

- [ ] 写 `docs/reviews/2026-09-28-sm8650-tlb-hierarchy.md`（四 Q 各自终态、报告三栏（实测/派生/解释）、来源三段分标（TRM/Explore/本机）、竞争解释）。
- [ ] 更新 `docs/open-items.md`（§11 各项落位）与 README（数据支持的口径）。
- [ ] 全量复验：CTest release+UBSan、runner、analysis、全部新 run schema+哈希、`git diff --check`、`git status`。
- [ ] 提交：`docs(sm8650): adjudicate TLB hierarchy campaign`。
- [ ] 按铁律 7 走退役流程（评审 → FF → main 复验 → 推送 → worktree/分支处置）。

**明确非目标（防 scope 蔓延）**：不新增线性遍历建链模式、不做路线 B、不输出 Q3 成本型数值、不碰 LLCC/cache 容量、不修改已冻结规则——任何偏离都先回任务书变更流程（新版本号 + exploratory 标记）。
