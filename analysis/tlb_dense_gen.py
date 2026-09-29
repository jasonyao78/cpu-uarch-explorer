# SPDX-License-Identifier: Apache-2.0
"""SM8650 X4 TLB Phase B 致密点生成器（任务书 v4.1 §6.2.4a/4b，确定性）。

Phase B 配置只由本模块从质量合格的 Phase A 数据确定性产出——不允许看
图后人工改点（§6.2 冻结纪律）。输出即
`configs/experiments/ptr-chase-sm8650-x4-tlb-dense.json` 的内容（dict，
调用方负责落盘），并附 plan 预览可消费的完整 execution 块；同一输入
必得同一输出（排序固定、无随机、无环境依赖）。

输入契约（`coarse_result`，由调用方从 `analysis.sm8650_tlb` 的
adjudicate_knee / detect_walk_onset 输出提取；本模块不回读原始曲线，
只消费下述标量与区间）：

```python
{
  "input_run_sha256": "…",   # Phase A run records.jsonl 的 SHA-256（64 位小写 hex）
  "knee":  {"intervals": [{"left": p_i, "right": p_{i+1},
                           "refill_ratio": float}, ...]},
  "onset": {"intervals": [ ... 同形 ... ]},
}
```

- knee.intervals = §6.2.2 提名的 Q1 候选区间（adjudicate_knee 的
  intervals）；refill_ratio = §6.2.2 条件 1 的 R_0x05(p_{i+1}) /
  R_0x05(p_i)。多 seed 提名同一区间时由调用方确定聚合口径（取各
  seed 最大比值——保留更强候选，与 §6.2.7 ①「保留相对增量大的」
  方向一致）；生成器只要求确定性正标量。
- onset.intervals = §6.2.3 的 walk-onset 区间（detect_walk_onset 的
  intervals）；refill_ratio 同口径取自粗扫曲线——onset 区间本身不经
  §6.2.2 提名，但 §6.2.7 ① 超支裁剪需要跨路径统一排序键（任务书沉
  默处取保守分支：由输入显式携带，生成器内不隐式假设）。
- 区间端点为页数（int，1 ≤ left < right，相邻粗扫点对由调用方担保）；
  同一路径内区间重复 = 契约缺项，DenseGenError。
- 两路径 intervals 皆空 → §6.2.8-7「皆无 → 不生成」，DenseGenError
  （Phase B 配置不得存在）；knee/onset 段缺省按空区间处理。生成门槛
  只看区间有无（§6.2.2「无候选 → Phase B 不生成」），不看 Q 级终态
  ——Phase A（2 seed × 短训练）自然落在 ORDER_/TRAINING_SENSITIVE，
  §6.2.6 稳定条件由 Phase B 数据判定，不是生成的前置。区间存活但插入
  点全空（合成小区间：Δ<4 四分位全部重合端点且 p_i/2 < 32）或全部被
  预算级联裁撤 → 致密点集合为空，同样 DenseGenError（fail-closed，
  不产出零 case 配置）。

生成规则（冻结）：

- §6.2.4a（knee 路径）：对每个候选区间 [p_i, p_{i+1}] 插入四分位点
  p_i + k·(p_{i+1} − p_i)/4（k=1,2,3，非整数页向下取整——p_i 为整数，
  即 p_i + ⌊k·Δ/4⌋）；若 p_i/2 ≥ 32 再插入 p_i/2（冻结粗扫阶梯页数
  全为偶数，整除恒等；奇数合成输入按同一向下取整方向处理，保证规则
  封闭）。候选区间 >3 个时按 R_0x05 相对增量降序取前 3，并列按 p_i
  升序（§6.2.8-4）。
- §6.2.4b（onset 路径，独立）：对 onset 区间应用与 4a 相同的插入规
  则；与 Q1 解耦——Q1 无候选而 Q2a 有 onset 时仍按本路径生成，两者
  都有点时按各自区间分别生成，跨区间去重后合入同一配置，逐点标注来
  源路径（knee/onset，见 generator.dense_points[].sources）。
- §6.2.8-2 区间内重合：取整后与本区间既有页点（区间端点 p_i/p_{i+1}
  或本区间已插入点）重合 → 丢弃该插入点，不计入该区间额度。「现有
  页点」= 本区间既有页点：粗扫阶梯上非端点的既有页点不在此列——计
  划 Task 7 测试向量①钉住该解读（[128,192] 的 p_i/2=64 虽为 Phase A
  粗扫点，仍插入并按 Phase B 协议复测）。
- §6.2.8-3 跨区间重合：同一页数被多个区间（含同区间被两路径各自提
  名）插入时，输出按页数去重为单个致密点（sources 列出全部来源），
  但重合点仍各占其来源区间的额度计数——防止合并后隐性超支：预算核
  算口径 quota_cases = Σ（每区间存活插入点数）× seed 数，而非去重后
  的 main_cases。
- §6.2.7 预算级联：主体 ≤ 50 case。quota_cases 超支时按裁剪优先级
  ①区间数（保留相对增量大的）执行——以与 §6.2.4a 相同的排序键
  （相对增量降序、并列按 p_i 升序）逐区间裁撤至 ≤50；knee/onset 同
  键竞争（onset 的 refill_ratio 由输入携带，见上）。完全并列（同区
  间同增量被两路径提名）时保留 knee 路径标注——§6.2.4 列举顺序
  4a 先于 4b，任务书沉默处的确定性取舍；两路径点位相同，裁撤只影
  响额度审计标注，不改致密点集合。≤3 区间 × ≤4 插入点 × 4 seed
  ≤ 48，级联①必然收敛，优先级②及以后在本配置（固定 4 seed × 短
  训练 × G0）不可达。长训练对照（≤12 case）与 G1（≤12 case）为独
  立额度、独立配置，不由本模块产出。

输出形状：完整 ExperimentSpec（protocol 1.2、G0 事件组、controls
["x4-prime"]、repetitions 10、base_pages=1、loads_per_slot=8、
min_loads=4096、warmup_passes=2、sweep={"buffer": [致密点升序],
"seed": [42, 7, 1337, 20260928]}）+ generator 审计块：
{input_run_sha256, rules_sha256, output_sha256} 三锚定（§6.2.4a「记录
输入 run SHA-256、规则块 SHA-256、输出配置 SHA-256」）+
rules_version（任务书版本标签）+ dense_points（逐点来源标注）+
quota（额度核算与裁剪审计）。output_sha256 的规范化口径：去掉
generator 块后的配置经 json.dumps(ensure_ascii=False, sort_keys=True,
separators=(",", ":")) 序列化（UTF-8）的 SHA-256。buffer 映射：页数
× 4 KiB（§6.2.1），整除 1024 KiB 时用 MiB 字符串（与粗扫配置一致）。
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path


class DenseGenError(ValueError):
    """致密点生成输入/规则锚定不满足契约（§6.2 冻结纪律，fail-closed）。"""


_EXPERIMENT_ID = "ptr-chase-sm8650-x4-tlb-dense"
# §7 Phase B / §6.2.7 ③ 的四个 order_seed（冻结顺序）
_SEEDS = (42, 7, 1337, 20260928)
_QUARTILE_K = (1, 2, 3)     # §6.2.4a 四分位 k=1,2,3
_HALF_MIN_PAGES = 32        # §6.2.4a：p_i/2 ≥ 32 才插入
_MAX_KNEE_INTERVALS = 3     # §6.2.4a：候选区间 >3 取前 3
_BUDGET_MAIN_CASES = 50     # §6.2.7：Phase B 主体 ≤ 50 case（锚点独立额度）
_PAGE_KIB = 4               # §6.2.1：buffer = pages × 4 KiB
_PATH_ORDER = {"knee": 0, "onset": 1}  # 输出排序固定（§6.2.4 列举顺序）

# G0 事件组（§5.2；与 ptr-chase-sm8650-x4-tlb-coarse.json 逐字一致）
_G0_PMU_EVENTS = (
    {"name": "cycles", "type": 8, "config": "0x11"},
    {"name": "mem_access_rd", "type": 8, "config": "0x66"},
    {"name": "l1d_tlb_refill", "type": 8, "config": "0x05"},
    {"name": "dtlb_walk", "type": 8, "config": "0x34"},
)

# §6.2 冻结规则块的提取标记（任务书章节标题行）
_RULES_BEGIN = "### 6.2"
_RULES_END = "### 6.3"
_DEFAULT_RULES_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs" / "tasks" / "2026-09-28-sm8650-tlb-hierarchy.md"
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _valid_sha256(value: object, context: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise DenseGenError(f"{context}: 64-char lowercase hex sha256 required "
                            f"({value!r})")
    return value


def _rules_block_sha256(path: str | Path) -> str:
    """任务书 §6.2 冻结规则块的 SHA-256。

    块 = 首个以 `### 6.2` 开头的行起，至其后首个以 `### 6.3` 开头的行
    （不含）止的原始文本（逐行保留原换行）。标记缺失或文件不可读 →
    DenseGenError：锚定对象不明确时不生成（fail-closed）。
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise DenseGenError(f"rules file {path}: unreadable ({exc})") from exc
    lines = text.splitlines(keepends=True)
    begin = next(
        (i for i, line in enumerate(lines) if line.startswith(_RULES_BEGIN)),
        None,
    )
    if begin is None:
        raise DenseGenError(
            f"rules file {path}: missing {_RULES_BEGIN!r} block start"
        )
    end = next(
        (i for i, line in enumerate(lines)
         if i > begin and line.startswith(_RULES_END)),
        None,
    )
    if end is None:
        raise DenseGenError(
            f"rules file {path}: missing {_RULES_END!r} block end"
        )
    return hashlib.sha256("".join(lines[begin:end]).encode("utf-8")).hexdigest()


def _validate_intervals(section: object, path_label: str) -> list[dict]:
    """单路径的区间列表校验与规范化；段缺省（None）按空区间处理。"""
    if section is None:
        return []
    if not isinstance(section, dict):
        raise DenseGenError(f"coarse_result[{path_label!r}]: object required")
    intervals = section.get("intervals", [])
    if not isinstance(intervals, list):
        raise DenseGenError(
            f"coarse_result[{path_label!r}].intervals: array required"
        )
    seen: set[tuple[int, int]] = set()
    normalized = []
    for entry in intervals:
        context = f"{path_label} interval {entry!r}"
        if not isinstance(entry, dict):
            raise DenseGenError(f"{context}: object with left/right/"
                                f"refill_ratio required")
        left, right = entry.get("left"), entry.get("right")
        if (type(left) is not int or type(right) is not int
                or not 1 <= left < right):
            raise DenseGenError(
                f"{context}: integer endpoints with 1 <= left < right required"
            )
        ratio = entry.get("refill_ratio")
        if (isinstance(ratio, bool) or not isinstance(ratio, (int, float))
                or not math.isfinite(ratio) or ratio <= 0):
            raise DenseGenError(
                f"{context}: positive finite refill_ratio required "
                f"({ratio!r})"
            )
        if (left, right) in seen:
            raise DenseGenError(f"{context}: duplicate interval "
                                f"({left}, {right})")
        seen.add((left, right))
        normalized.append({"left": left, "right": right,
                           "refill_ratio": float(ratio)})
    return normalized


def _interval_insertions(left: int, right: int) -> tuple[list[int], list[int]]:
    """§6.2.4a/4b 插入规则 + §6.2.8-2 区间内重合丢弃。

    返回 (inserted_pages 升序, dropped_pages 升序)。四分位点非整数页向
    下取整（p_i 整数 ⇒ floor(p_i + k·Δ/4) = p_i + ⌊k·Δ/4⌋）；p_i/2 ≥ 32
    再插入。取整后与本区间既有页点（端点 p_i/p_{i+1} 或本区间已插入
    点）重合 → 丢弃且不计入该区间额度（§6.2.8-2）。
    """
    delta = right - left
    candidates = [left + (k * delta) // 4 for k in _QUARTILE_K]
    half = left // 2
    if half >= _HALF_MIN_PAGES:
        candidates.append(half)
    inserted: list[int] = []
    dropped: list[int] = []
    for point in candidates:
        if point in (left, right) or point in inserted:
            dropped.append(point)
        else:
            inserted.append(point)
    return sorted(inserted), sorted(dropped)


def _retention_key(entry: dict) -> tuple:
    """保留优先级排序键（升序 = 优先保留）：§6.2.4a/§6.2.8-4/§6.2.7 ①
    共用——相对增量降序、并列按 p_i 升序（再按右端点与路径保证全序；
    完全并列保留 knee，见模块 docstring）。"""
    return (-entry["refill_ratio"], entry["left"], entry["right"],
            _PATH_ORDER[entry["path"]])


def _pages_to_buffer(pages: int) -> str:
    """页数 → buffer 尺寸字符串（pages × 4 KiB，§6.2.1；整除 1024 KiB
    时用 MiB，与粗扫配置写法一致）。"""
    kib = pages * _PAGE_KIB
    return f"{kib // 1024}MiB" if kib % 1024 == 0 else f"{kib}KiB"


def _resolve_rules_sha256(rules_sha256: str | None,
                          rules_path: str | Path | None) -> str:
    """rules_sha256 由调用方显式传入，或从任务书文件（rules_path，缺省
    仓内任务书）计算；两者同给 = 来源不明，DenseGenError。"""
    if rules_sha256 is not None and rules_path is not None:
        raise DenseGenError(
            "rules_sha256 and rules_path are mutually exclusive"
        )
    if rules_sha256 is not None:
        return _valid_sha256(rules_sha256, "rules_sha256")
    return _rules_block_sha256(rules_path or _DEFAULT_RULES_PATH)


def emit_dense_config(coarse_result: dict, rules_version: str, *,
                      rules_sha256: str | None = None,
                      rules_path: str | Path | None = None) -> dict:
    """从 Phase A 粗扫裁决结果确定性生成 Phase B 致密扫描配置。

    coarse_result 形状见模块 docstring 输入契约；rules_version 为任务书
    版本标签（如 "v4.1"，随 generator 块入档）。rules_sha256 缺省时从
    仓内任务书提取 §6.2 规则块计算（_DEFAULT_RULES_PATH）。返回完整
    ExperimentSpec dict（含 generator 三 SHA-256 审计块），调用方负责
    落盘为 ptr-chase-sm8650-x4-tlb-dense.json 并跑 plan 预览核对。
    两路径皆无候选 → §6.2.8-7 DenseGenError（不生成）。
    """
    if not isinstance(coarse_result, dict):
        raise DenseGenError("coarse_result: object required")
    input_sha = _valid_sha256(coarse_result.get("input_run_sha256"),
                              "coarse_result.input_run_sha256")
    knee_intervals = _validate_intervals(coarse_result.get("knee"), "knee")
    onset_intervals = _validate_intervals(coarse_result.get("onset"), "onset")
    if not knee_intervals and not onset_intervals:
        raise DenseGenError(
            "§6.2.8-7: Q1 无候选且 Q2a 无 onset —— Phase B 不生成"
        )
    if not isinstance(rules_version, str) or not rules_version:
        raise DenseGenError(
            f"rules_version: non-empty string required ({rules_version!r})"
        )
    rules_hash = _resolve_rules_sha256(rules_sha256, rules_path)

    # §6.2.4a：候选区间 >3 个时按 R_0x05 相对增量取前 3（并列按 p_i 升
    # 序，§6.2.8-4）。onset 路径无 >3 裁剪规则（每 seed 至多一个 onset
    # 区间），只按端点排序固定顺序；超支统一由 §6.2.7 级联①处理。
    clipped: list[dict] = []
    knee_sorted = sorted(
        ({"path": "knee", **entry} for entry in knee_intervals),
        key=_retention_key,
    )
    for entry in knee_sorted[_MAX_KNEE_INTERVALS:]:
        clipped.append({
            "path": "knee",
            "interval_pages": [entry["left"], entry["right"]],
            "refill_ratio": entry["refill_ratio"],
            "reason": ("§6.2.4a: candidate intervals > 3, keep top 3 by "
                       "R_0x05 relative increment (ties by p_i ascending, "
                       "§6.2.8-4)"),
        })
    surviving = knee_sorted[:_MAX_KNEE_INTERVALS] + sorted(
        ({"path": "onset", **entry} for entry in onset_intervals),
        key=lambda entry: (entry["left"], entry["right"]),
    )

    for entry in surviving:
        inserted, dropped = _interval_insertions(entry["left"], entry["right"])
        entry["inserted_pages"] = inserted
        entry["dropped_pages"] = dropped
        entry["quota_points"] = len(inserted)

    # §6.2.7 预算级联：quota_cases（重合点各占来源区间额度，§6.2.8-3）
    # 超 50 时按优先级①区间数逐区间裁撤（保留相对增量大的，同
    # _retention_key）。≤3 区间 × ≤4 插入点 × 4 seed ≤ 48，级联必然收敛。
    surviving.sort(key=_retention_key)
    while (surviving
           and sum(entry["quota_points"] for entry in surviving) * len(_SEEDS)
           > _BUDGET_MAIN_CASES):
        dropped = surviving.pop()  # 保留优先级最差者（升序尾部）
        clipped.append({
            "path": dropped["path"],
            "interval_pages": [dropped["left"], dropped["right"]],
            "refill_ratio": dropped["refill_ratio"],
            "reason": ("§6.2.7 budget cascade ①: drop interval with smallest "
                       "relative increment until main budget <= 50 cases"),
        })

    # 跨区间/跨路径按页数去重合入（§6.2.8-3），逐点标注来源路径；页数升序
    by_pages: dict[int, dict] = {}
    for entry in surviving:
        for pages in entry["inserted_pages"]:
            point = by_pages.setdefault(pages, {"pages": pages, "sources": []})
            point["sources"].append({
                "path": entry["path"],
                "interval_pages": [entry["left"], entry["right"]],
            })
    dense_points = []
    for pages in sorted(by_pages):
        point = by_pages[pages]
        point["sources"].sort(key=lambda source: (
            _PATH_ORDER[source["path"]],
            source["interval_pages"][0],
            source["interval_pages"][1],
        ))
        dense_points.append({
            "pages": pages,
            "buffer": _pages_to_buffer(pages),
            "sources": point["sources"],
        })
    if not dense_points:
        # 区间存活但插入点全空/全被裁 → 零 case 配置无意义，fail-closed
        raise DenseGenError(
            "致密点集合为空（区间过小或全部被预算级联裁撤）——不生成 "
            "Phase B 配置"
        )

    per_interval = [
        {
            "path": entry["path"],
            "interval_pages": [entry["left"], entry["right"]],
            "refill_ratio": entry["refill_ratio"],
            "inserted_pages": entry["inserted_pages"],
            "dropped_pages": entry["dropped_pages"],
            "quota_points": entry["quota_points"],
        }
        for entry in sorted(surviving, key=lambda entry: (
            _PATH_ORDER[entry["path"]], entry["left"], entry["right"]))
    ]
    clipped.sort(key=lambda entry: (
        _PATH_ORDER[entry["path"]], entry["interval_pages"][0],
        entry["interval_pages"][1]))
    point_quota_total = sum(entry["quota_points"] for entry in surviving)
    quota = {
        "unit": ("runner case = buffer × order_seed × 训练量 × 事件组 × "
                 "policy（§6.2.7）；锚点 2 run 为独立额度，不在此计数"),
        "budget_main_cases": _BUDGET_MAIN_CASES,
        "seeds": list(_SEEDS),
        # §6.2.8-3：预算核算口径（重合点各占来源区间额度，防合并后隐性超支）
        "quota_cases": point_quota_total * len(_SEEDS),
        # 去重合并后实际 runner case 数（≤ quota_cases）
        "main_cases": len(dense_points) * len(_SEEDS),
        "point_quota_total": point_quota_total,
        "per_interval": per_interval,
        "clipped_intervals": clipped,
    }

    buffers = [point["buffer"] for point in dense_points]
    config = {
        "schema_version": "1.0",
        "id": _EXPERIMENT_ID,
        "title": ("SM8650 X4 TLB Phase B 致密扫描（§6.2.4a/4b 确定性生成器"
                  "产出）"),
        "protocol_version": "1.2",
        "harness": "portable",
        "parameters": [
            {"name": "buffer", "type": "size",
             "range": (f"致密点 {dense_points[0]['pages']}.."
                       f"{dense_points[-1]['pages']} 页共 {len(dense_points)} 档"
                       f"（§6.2.4a/4b 生成，pages × 4KiB 映射）")},
            {"name": "stride", "type": "size", "default": "64B"},
            {"name": "warmup_passes", "type": "int", "default": 2},
            {"name": "loads_per_slot", "type": "int", "default": 8},
            {"name": "min_loads", "type": "int", "default": 4096},
            {"name": "repetitions", "type": "int", "default": 10},
            {"name": "base_pages", "type": "int", "default": 1},
            {"name": "seed", "type": "int", "default": 42},
            {"name": "pmu_events", "type": "pmu-event-list",
             "default": [dict(event) for event in _G0_PMU_EVENTS]},
        ],
        "preconditions": [
            "redmi-k70pro-01 controlled-baseline profile 前后门禁通过",
            "CPU7 Cortex-X4；四个 core PMU event 同窗且 "
            "time_running == time_enabled（拒绝复用）",
            "每个 repetition 为新进程/新匿名映射；actual backing 必须为 "
            "base；逐样本 seed 入档",
            "输入 = 通过质量门槛的 Phase A 数据（§6.2.4）；点位由生成器"
            "确定性产出，禁止看图后人工改点/改阈值/删 seed",
        ],
        "metrics": [
            {"name": "latency_ns", "unit": "ns", "statistic": "median"},
            {"name": "pmu.cycles.count", "unit": "events",
             "statistic": "median"},
            {"name": "pmu.mem_access_rd.count", "unit": "events",
             "statistic": "median"},
            {"name": "pmu.l1d_tlb_refill.count", "unit": "events",
             "statistic": "median"},
            {"name": "pmu.dtlb_walk.count", "unit": "events",
             "statistic": "median"},
        ],
        "execution": {
            "probe": "ptr_chase",
            "controls": ["x4-prime"],
            "params": {"repetitions": 10},
            "sweep": {"buffer": buffers, "seed": list(_SEEDS)},
            "fixed_params": [
                "stride", "warmup_passes", "loads_per_slot", "min_loads",
                "base_pages", "pmu_events",
            ],
        },
        "notes": (
            f"Phase B 致密扫描（任务书 §6.2.4a/4b 生成器产出）："
            f"{len(dense_points)} 个致密点 × order_seed {list(_SEEDS)} × "
            f"短训练（loads_per_slot=8）× G0 = {quota['main_cases']} case"
            f"（§6.2.7 主体额度 ≤{_BUDGET_MAIN_CASES}；预算核算口径 "
            f"{quota['quota_cases']} case，见 generator.quota）；长训练对"
            f"照（≤12 case）与 G1（≤12 case）为独立额度/独立配置，不在本"
            f"文件。点位来源路径（knee/onset）逐点标注于 "
            f"generator.dense_points；输入 run/规则块/输出配置三 SHA-256 "
            f"锚定见 generator 块。"
        ),
    }

    # output_sha256：去掉 generator 块的规范化 JSON（sort_keys + 紧凑分
    # 隔符，UTF-8）的 SHA-256——口径固定，可复算。
    canonical = json.dumps(config, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    config["generator"] = {
        "input_run_sha256": input_sha,
        "rules_sha256": rules_hash,
        "output_sha256": hashlib.sha256(canonical).hexdigest(),
        "rules_version": rules_version,
        "dense_points": dense_points,
        "quota": quota,
    }
    return config
