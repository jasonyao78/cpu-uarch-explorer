# SPDX-License-Identifier: Apache-2.0
"""SM8650 X4 TLB 战役图表生成器（终审同事版：四张 SVG + report.md）。

CLI：python -m analysis.tlb_figures --runs-root data/public/runs --out <目录>

run 名单与 (buffer × seed) 网格均为模块常量钉死（出处：任务书 v4.4 §7
Phase A/B/D 配置 + 战役终审 docs/reviews/2026-09-28-sm8650-tlb-hierarchy.md
§1/§2）。数据纪律：只读 records.jsonl；逐样本消费走
analysis.sm8650_tlb.analyze_records 的证据契约（G0 metric 集、逐样本
对齐、multiplex 拒绝）；中位数一律经 runner.statistics.summarize；无
时钟/随机/环境依赖，同输入必同输出。事件资格门控是判定器职责（终审
已完成），本模块渲染已终审数据，不消费注册表。

曲线构造（图 1–3）：每 (buffer_kb, seed) 取组中位数 → 跨 seed 合并 =
各 seed 中位数的中位数（确定性）；粗扫与致密的重合点（4096 KiB）按同
(buffer, seed) 跨 run 先合并（各 run 组中位数的中位数）。逐点合并暴
露为纯函数 seed_medians / merge_seed_medians / curve_from_groups。

图 4 只消费 grade_thp_cohorts 的分级产出（不自建分组）：只画比较级单
元的 cohort median——描述级按任务书 §7 Phase D 纪律不出 median、不
足级无观测可画；同 (buffer × cohort) 多个比较级单元（未跨 seed 合并）
取单元中位数的中位数作为展示值，分级明细随 report.md 原样披露。

fail-closed（同 analysis.cli 退出码阶梯，1 = 输入错误）：缺 run
（FileNotFoundError）、契约缺项（TlbError）、失败记录非零（钉死数据
集应为全 ok 判定 run）、(buffer × seed) 网格不符、ring passes ≠ 8、
空系列，任一即非零退出 + stderr 说明。
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from runner.statistics import summarize

from .chart import latency_svg
from .load import load_run
from .sm8650_tlb import TlbError, analyze_records, grade_thp_cohorts

# 钉死的战役数据集（出处见模块 docstring）
RUN_COARSE = "20260930T004843Z-ptr-chase-sm8650-x4-tlb-coarse"   # 粗扫：13 档 × seed{7,42}，8 环
RUN_DENSE = "20260930T010808Z-ptr-chase-sm8650-x4-tlb-dense"     # 致密：8 档 × 4 seed，8 环
RUN_THP_BASE = "20260930T014014Z-ptr-chase-sm8650-x4-tlb-thp-base"        # Phase D -B：3 点 × 4 seed
RUN_THP_MADVISE = "20260930T013743Z-ptr-chase-sm8650-x4-tlb-thp-madvise"  # Phase D -T：3 点 × 4 seed

COARSE_BUFFERS = (128, 256, 384, 512, 768, 1024, 1536, 2048, 3072, 4096,
                  8192, 16384, 32768)
COARSE_SEEDS = (7, 42)
DENSE_BUFFERS = (192, 416, 448, 480, 4096, 10240, 12288, 14336)
DENSE_SEEDS = (7, 42, 1337, 20260928)
THP_BUFFERS = (512, 2304, 3072)
THP_SEEDS = (7, 42, 1337, 20260928)

_FORMAL_RING_PASSES = 8  # 协议正式窗口（任务书 §6.1：8 ring passes）
# 图 4 只画 2304/3072 两点（512 KiB 是策略负控，不进对照图——终审 §3 Q4）
THP_FIGURE_BUFFERS = (2304, 3072)
# 图 4 按实际 backing 分系列；thp cohort 本次未出现（转化表见终审 §3 Q4）
_THP_FIGURE_COHORTS = ("base", "mixed")

_F_REFILL = "l1d_tlb_refill_per_1k"
_F_WALK = "dtlb_walk_per_1k"


def seed_medians(groups: list[dict], field: str,
                 skipped: list[dict] | None = None) -> dict[tuple[int, int], float]:
    """{(buffer_kb, seed): 该点组中位数}；同 (buffer, seed) 跨 run 重合时
    合并为各 run 组中位数的中位数（summarize，确定性）。

    只消费 base backing 组：扫描曲线合并不同 backing 会静默混淆页策略
    制度（mixed/thp 的 refill 形态与 base 完全不同），非 base 组即
    TlbError fail-closed。
    REV-M0-BATCH MB-04：非 legacy 身份（chains/分布/offset 等实验条件）
    拒绝进入扫描曲线（禁止跨条件无声合并），需显式分系列规则。
    REV-M0-BATCH MB-07：None（降级字段）点不进曲线但必须进 skipped
    审计清单（run/buffer/seed/field），由调用方披露——禁止静默删点。
    """
    by_point: dict[tuple[int, int], list[float]] = defaultdict(list)
    for group in groups:
        label = group.get('run_label', '?')
        if group["page_policy_actual"] != "base":
            raise TlbError(
                f"{label}: 扫描曲线只消费 base backing 组，"
                f"got {group['page_policy_actual']!r}（buffer={group['buffer_kb']}KiB，"
                f"防静默合并不同 backing）"
            )
        identity = group.get("identity")
        if identity and any(value is not None for value in identity.values()):
            raise TlbError(
                f"{label}: 非 legacy identity {identity}（MB-04：扫描曲线"
                f"禁止跨条件合并；buffer={group['buffer_kb']}KiB）"
            )
        stats = group.get(field)
        if stats is None:
            if skipped is not None:
                skipped.append({
                    "run": label, "buffer_kb": group["buffer_kb"],
                    "seed": group["seed"], "field": field,
                })
            continue
        by_point[(group["buffer_kb"], group["seed"])].append(stats["median"])
    return {point: summarize(medians)["median"]
            for point, medians in sorted(by_point.items())}


def merge_seed_medians(per_seed: dict[tuple[int, int], float]) -> list[tuple[int, float]]:
    """跨 seed 合并 = 各 seed 中位数的中位数 → [(buffer_kb, y)] 按 buffer 排序。"""
    by_buffer: dict[int, list[float]] = defaultdict(list)
    for (buffer_kb, _seed), median in per_seed.items():
        by_buffer[buffer_kb].append(median)
    return [(buffer_kb, summarize(by_buffer[buffer_kb])["median"])
            for buffer_kb in sorted(by_buffer)]


def curve_from_groups(groups: list[dict], field: str,
                      skipped: list[dict] | None = None) -> list[tuple[int, float]]:
    """analyze_records 分组 → 合并曲线 [(buffer_kb, 中位数)]（两步合并的组合）。"""
    return merge_seed_medians(seed_medians(groups, field, skipped=skipped))


def cohort_series(graded: dict, buffers: tuple[int, ...] = THP_FIGURE_BUFFERS,
                  field: str = _F_REFILL) -> dict[str, list[tuple[float, float]]]:
    """grade_thp_cohorts 产出 → {cohort: [(buffer_kb, median)]}（图 4 系列）。

    只画比较级单元的 stats median；同 (buffer × cohort) 多个比较级单元
    （regime 不一致未跨 seed 合并）取单元中位数的中位数。分组权威始终是
    grade_thp_cohorts，本函数不做任何重新分组。
    """
    series: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for entry in graded["cohorts"]:
        if entry["buffer_kb"] not in buffers:
            continue
        # REV-M0-BATCH C5：同上，降级单位的该字段为 None 时跳过
        medians = [unit["stats"][field]["median"]
                   for unit in entry["units"] if unit["grade"] == "comparative"
                   and unit["stats"].get(field) is not None]
        if medians:
            series[entry["cohort"]].append(
                (float(entry["buffer_kb"]), summarize(medians)["median"]))
    for points in series.values():
        points.sort()
    return dict(series)


def cohort_grading_lines(graded: dict,
                         buffers: tuple[int, ...] = THP_FIGURE_BUFFERS) -> list[str]:
    """grade_thp_cohorts 产出的可审计分级明细（markdown 行；输出本身有序）。"""
    lines = []
    for entry in graded["cohorts"]:
        if entry["buffer_kb"] not in buffers:
            continue
        units = []
        for unit in entry["units"]:
            seg = (f"seed{'/'.join(str(s) for s in unit['seeds'])} "
                   f"{unit['grade']} n={unit['valid_samples']}")
            if unit.get("terminal"):
                seg += f"（终态 {unit['terminal']}）"
            units.append(seg)
        lines.append(f"- {entry['buffer_kb']} KiB × {entry['cohort']}"
                     f"（跨 seed 合并={entry['merged']}）：" + "；".join(units))
    return lines


def _load_run_groups(runs_root: Path, name: str, buffers: tuple[int, ...],
                     seeds: tuple[int, ...]) -> list[dict]:
    """加载单个钉死 run 并校验网格形状（fail-closed）。"""
    run = load_run(runs_root / name)  # 缺 run → FileNotFoundError 上抛
    if run.failed_records:
        raise TlbError(f"{name}: {len(run.failed_records)} failed records "
                       f"（钉死数据集应为全 ok 判定 run）")
    result = analyze_records(run.ok_records, name)
    grid = {(group["buffer_kb"], group["seed"]) for group in result.groups}
    expected = {(b, s) for b in buffers for s in seeds}
    missing, extra = expected - grid, grid - expected
    if missing or extra:
        raise TlbError(f"{name}: (buffer, seed) 网格不符"
                       f"（缺 {sorted(missing)}，多 {sorted(extra)}）")
    for group in result.groups:
        if group["ring_passes"] != _FORMAL_RING_PASSES:
            raise TlbError(f"{name}: ring_passes={group['ring_passes']} "
                           f"!= {_FORMAL_RING_PASSES}（非正式窗口不入图）")
    return result.groups


def load_campaign(runs_root: Path) -> tuple[list[dict], list[dict]]:
    """钉死名单 4 run → (扫描组, Phase D 组)（analyze_records 分组产出）。"""
    scan = []
    for name, buffers, seeds in (
        (RUN_COARSE, COARSE_BUFFERS, COARSE_SEEDS),
        (RUN_DENSE, DENSE_BUFFERS, DENSE_SEEDS),
    ):
        scan.extend(_load_run_groups(runs_root, name, buffers, seeds))
    thp = []
    for name in (RUN_THP_BASE, RUN_THP_MADVISE):
        thp.extend(_load_run_groups(runs_root, name, THP_BUFFERS, THP_SEEDS))
    return scan, thp


def build_figures(scan_groups: list[dict], graded: dict,
                  audit: dict | None = None) -> dict[str, str]:
    """扫描分组 + cohort 分级 → {文件名: SVG}（四图；空系列 fail-closed）。

    audit（可选 out 参数）收集 {"skipped_points": [...]}——MB-07 披露通道：
    部分缺点时曲线照画但缺点清单必须随报告/审计走。
    """
    skipped: list[dict] = []
    curves = {
        _F_REFILL: curve_from_groups(scan_groups, _F_REFILL, skipped=skipped),
        _F_WALK: curve_from_groups(scan_groups, _F_WALK, skipped=skipped),
        "latency_ns": curve_from_groups(scan_groups, "latency_ns", skipped=skipped),
        "cyc_per_load": curve_from_groups(scan_groups, "cyc_per_load", skipped=skipped),
    }
    if audit is not None:
        audit["skipped_points"] = skipped
    for field, points in curves.items():
        if not points:
            # MB-07：空系列错误必须点名跳过点（run/buffer/seed/field）
            raise TlbError(
                f"scan curve {field}: 空系列（fail-closed）；"
                f"降级跳过点 {skipped[:8]}"
                + (" …" if len(skipped) > 8 else "")
            )
    cohorts = cohort_series(graded)
    for cohort in _THP_FIGURE_COHORTS:
        if not cohorts.get(cohort):
            raise TlbError(f"cohort {cohort}: 无比较级单元可画（空系列 fail-closed）")
    return {
        # 图 1：Q1 转折区（480 KiB–4 MiB = [120,1024] 页，终审 §1）
        "refill-density.svg": latency_svg(
            {"R_0x05 refill/1k": curves[_F_REFILL]},
            "L1 dTLB refill 密度 vs buffer（SM8650 X4，8 环，跨 seed 中位数）",
            y_label="R_0x05 refill 密度 /1k loads（log2）",
            shaded=[(480, 4096, "Q1 转折区 [120,1024] 页")]),
        # 图 2：Q2a onset（10–12 MiB = [2560,3072] 页）+ MMUTC 2048 项参
        # 考线（2048 页 × 4 KiB = 8192 KiB；TRM Table 6-1，假设级联想）
        "walk-onset.svg": latency_svg(
            {"R_0x34 walk/1k": curves[_F_WALK]},
            "dtlb walk 密度 vs buffer（SM8650 X4，8 环，跨 seed 中位数）",
            y_label="R_0x34 walk 密度 /1k loads（log2）",
            shaded=[(10240, 12288, "Q2a onset [2560,3072] 页")],
            vlines=[(8192, "MMUTC 2048 项（TRM，假设级联想）")]),
        # 图 3：延迟与 TLB 事件不是一回事的对照（终审 §3 Q3 反相关）
        "latency-cycles.svg": latency_svg(
            {"latency_ns": curves["latency_ns"],
             "cycles/load": curves["cyc_per_load"]},
            "延迟与 cycles/load vs buffer（对照：延迟与 TLB 事件不是一回事）",
            y_label="latency_ns / cycles per load（log2）"),
        # 图 4：Q4 THP cohort（按实际 backing；只画比较级 median）
        "thp-cohort.svg": latency_svg(
            cohorts,
            "THP cohort 对照：R_0x05 refill/1k（按实际 backing，比较级中位数）",
            y_label="R_0x05 refill 密度 /1k loads（log2）"),
    }


# --- report.md 读法文本（同事版，无微架构背景假设；内容规格 = 任务要求 §3） ---

_INTRO = (
    "> 面向无微架构背景的同事：四张图 + 大白话读法。终态口径以战役终审 "
    "`docs/reviews/2026-09-28-sm8650-tlb-hierarchy.md` 为准（本报告是它的图表附件）。"
    "报告由 `python -m analysis.tlb_figures` 生成：只读 `records.jsonl`"
    "（中位数经 `runner.statistics.summarize`），无时钟/随机/环境依赖，同输入必同输出。"
)

_BACKGROUND = (
    "TLB（Translation Lookaside Buffer）是「虚拟页 → 物理页」翻译的缓存：程序每访问一次"
    "内存，CPU 都要把虚拟页号翻译成物理页号，TLB 缓存最近用过的翻译，免得每次都走内存里的"
    "页表。本战役用指针追逐负载逐级加大程序同时使用的内存量：buffer 越大、用到的页数越多"
    "（4 KiB 一页），TLB 压力越大。测试机 redmi-k70pro-01（SM8650 Cortex-X4 核），全部数字"
    "为 8 环正式窗口下逐进程样本的中位数口径。"
)

_FIG1_READING = (
    "**怎么读**：TLB 是页表翻译的缓存；横轴是程序正在用的内存量（换算成页数 = KiB ÷ 4），"
    "纵轴是每 1000 次访问里有多少次要重填 L1 TLB。灰蓝区（480 KiB–4 MiB，对应 120–1024 页）"
    "是终审判定的转折区：进入灰蓝区前已开始陡升（384→480 KiB "
    "从 ~4 到 ~235/1k），区内继续爬升到超过每次访问一次——这一片宽区间就是「L1 TLB 开始"
    "不够用」的区域。注意两点：它不是悬崖而是缓坡；纵轴超过 1000/1k 并不矛盾——它是"
    "事件密度而不是概率（一次访问可能触发多次重填事件）。"
)

_FIG2_READING = (
    "**怎么读**：这条曲线回答「什么时候连片上缓存都救不了、必须走内存里的页表」——这个动作"
    "叫 page table walk。4 MiB 以下几乎为零；8 MiB 已明显抬升（≈10/1k，约地板的 65 倍）；"
    "10–12 MiB 全开（≈50/1k）——onset 判定区间 [2560,3072] 页是全开段，抬升从它左边已经"
    "开始。竖虚线是芯片手册（TRM）写的 MMUTC 2048 项参考位置（2048 页 × 4 KiB = 8 MiB）："
    "walk onset 落在它右边，这件事目前只是机制联想，不是证明。"
)

_FIG3_READING = (
    "**怎么读**：延迟和 TLB 事件不是一回事。中段（约 4 MiB）延迟最高时 walk 还没开始，"
    "walk 开始后延迟反而下降——中段由 L1 refill 风暴主导（图 1 里 >1000/1k 的区间），其成本"
    "高过 onset 后的 walk 服务。所以本报告的结论都不画在延迟轴上；这张图只是对照，提醒"
    "「看延迟猜 TLB」会误判。"
)

# 注意：本段含静态数字（-82%、-12.4%、转化表 base 25 + mixed 15、n=5）——
# 数据集修订（revision history）时需与 grade_thp_cohorts 产出手动同步；
# report.md 里的分级明细行是生成的（自动跟踪），本段读法文本是常量。
_FIG4_READING = (
    "**怎么读**：进程内部分页拿到大页（THP，2 MiB 一页）的 cohort，TLB 压力掉到约 1/5"
    "（3072 KiB 处 R_0x05 **-82%**），延迟 **-12.4%**。但只有一部分进程真的拿到了大页"
    "（3072 KiB 转化表：40 进程次中 base 25 + mixed 15），其余仍用普通 4 KiB 页。图上只画"
    "达到「比较级」（≥5 有效样本）的 cohort 中位数：3072 KiB 的 mixed 只有 seed42 达标"
    "（n=5）；2304 KiB 的 mixed 全体 INSUFFICIENT_COHORT，如实不出点。"
)

_FINAL_STATES = (
    "| Q | 终态 | 结果 |\n"
    "|---|---|---|\n"
    "| Q1 `0x05` 第一有效转折 | INTERVAL_IDENTIFIED | [120, 1024] 页（480 KiB–4 MiB），"
    "宽饱和区而非锐边；4 seed × 双训练量同区间 |\n"
    "| Q2a `0x34` walk-onset | INTERVAL_IDENTIFIED | [2560, 3072] 页（10–12 MiB）；"
    "4 seed × 双训练量一致 |\n"
    "| Q2b L2 层级辨识 | 降级完成 | `0x2d`（unified refill）QUALIFIED；"
    "`0x2f` SEMANTICS_UNVERIFIED |\n"
    "| Q2c 第二级 effective reach | 未授权（OPEN） | 授权门槛未满足，不结案 |\n"
    "| Q3 walk 暴露成本 | MODEL_UNIDENTIFIABLE | walk 密度与延迟/cyc 反相关，单调性不成立；"
    "MMUTC 混杂未分离 |\n"
    "| Q4 THP cohort 对照 | 机制方向一致（受限比较级） | 3072 mixed（seed42，n=5）延迟 "
    "-12.4%、R_0x05 -82%；2304 mixed 与 3072 其余 seed = INSUFFICIENT_COHORT |"
)

_NOT_MEASURED = (
    "- **TLB 物理项数没有测出来**，也不能由本协议报出：固定随机环访问分不清容量、预取与"
    "页布局各自的贡献（同一条曲线三种解释都兼容）。要测需要可控布局探针——已登记备选"
    "（`docs/open-items.md` OI-14，条件后置）。\n"
    "- **Q2c（L2 TLB 容量 / effective reach）未授权**：`0x2f` 事件语义未核实 + 授权门槛"
    "未满足，保持 OPEN，不由 walk-onset 区间外推。\n"
    "- 图上的「页数」全部按 4 KiB base 页换算；TRM 的 MMUTC 2048 项只是参考线（假设级联想），"
    "不构成结构证明。"
)

_REPRODUCE = (
    "- 本报告全部图表再生（同输入必同输出）：\n"
    "  `python -m analysis.tlb_figures --runs-root data/public/runs --out <目录>`\n"
    "- 终态数字的复算入口：判定分析器 `analysis/sm8650_tlb.py`（knee / walk-onset / THP "
    "cohort 分级等冻结规则）与战役终审 `docs/reviews/2026-09-28-sm8650-tlb-hierarchy.md`"
    "（§1 终态总表 + §3 分 Q 证据）。"
)


# 缺点数据再生成时的顶部警示（MB-07 收口复核）：终态表与图读法是冻结
# 历史终态的引用，不是对当前缺点曲线的重判结果。
_DEGRADED_BANNER = (
    "> ⚠️ **缺点数据再生成**：输入数据集不完整（见末节「数据局限」）。"
    "本报告未对缺点数据执行重判：终态表与图读法均为 2026-09-28 冻结历史"
    "终态的引用；凡当前曲线不再支撑的区间/读法，已就地标注"
    "「当前曲线不支持」，完整网格恢复前不应引用被标注内容。"
)


def _mask_claim(text: str, interval: str, supported: bool) -> str:
    """缺点数据下就地标注当前曲线不支持的判定区间/读法（MB-07 收口复核）。

    supported=True（或 interval 不在文本中）时原文返回——完整数据路径
    逐字不变；supported=False 时区间前加「当前曲线不支持〕」标注，禁止
    把历史结论当作本次生成结果。"""
    if supported or interval not in text:
        return text
    return text.replace(interval, f"〔当前曲线不支持〕{interval}")


# 冻结判定区间（终审 §1）对应的曲线覆盖范围，单位 KiB：缺点数据下
# 区间内无可用点即视为该判定不受当前曲线支持。
_KNEE_REGION_KB = (480, 4096)        # Q1 [120, 1024] 页
_WALK_ONSET_REGION_KB = (10240, 12288)  # Q2a [2560, 3072] 页（10–12 MiB）


def _final_states_for(claim_support: dict[str, bool] | None) -> str:
    """终态表文本：按当前曲线支持度就地标注不受支持的判定区间。

    仅在缺点数据模式下被调用；claim_support=None（未评估）按全不支持
    保守标注——历史引用宁可多标，不可把无支撑判定当有效区间输出。"""
    support = claim_support or {}
    text = _mask_claim(
        _FINAL_STATES, "[120, 1024] 页（480 KiB–4 MiB）",
        support.get("refill_knee", False))
    text = _mask_claim(
        text, "[2560, 3072] 页（10–12 MiB）",
        support.get("walk_onset", False))
    return text


def build_report(graded: dict, skipped_points: list[dict] | None = None,
                 claim_support: dict[str, bool] | None = None) -> str:
    """生成同事版 report.md：四图嵌入 + 读法 + 终态表 + 边界 + 复算指引。

    skipped_points（MB-07 披露）：非空时附"数据局限"段，逐点列出被降级
    跳过、未进曲线的 (run, buffer, seed, field)；同时进入缺点数据模式——
    顶部加警示横幅，终态表标题改为"历史终审引用（非本数据集重判）"，
    图读法/终态区间按 claim_support 就地标注支持度（缺省 = 全部不支持，
    保守 fail-closed）。claim_support 键：refill_knee / walk_onset。"""
    degraded = bool(skipped_points)
    fig1_reading = _mask_claim(
        _FIG1_READING, "（480 KiB–4 MiB，对应 120–1024 页）",
        True if not degraded
        else (claim_support or {}).get("refill_knee", False))
    fig2_reading = _mask_claim(
        _FIG2_READING, "[2560,3072]",
        True if not degraded
        else (claim_support or {}).get("walk_onset", False))
    final_states = (_final_states_for(claim_support) if degraded
                    else _FINAL_STATES)
    final_heading = ("## 终态表（历史终审引用：2026-09-28 冻结；非本数据集重判）"
                     if degraded
                     else "## 终态表（终审 §1，每 Q 独立）")
    lines = [
        "# SM8650 X4 TLB 战役：同事版图表与读法",
        "",
        _INTRO,
        "",
        *([_DEGRADED_BANNER, ""] if degraded else []),
        "## 一分钟背景",
        "",
        _BACKGROUND,
        "",
        "## 数据来源（钉死的战役数据集）",
        "",
        f"- 粗扫 `{RUN_COARSE}`：13 档 buffer × seed{{7,42}}，8 环；",
        f"- 致密 `{RUN_DENSE}`：8 档 × 4 seed，8 环（4096 KiB 与粗扫重合，逐 seed 合并中位数）；",
        f"- Phase D `-B` `{RUN_THP_BASE}` / `-T` `{RUN_THP_MADVISE}`：各 3 点 × 4 seed。",
        "",
        "曲线构造：每 (buffer, seed) 取组中位数，跨 seed 合并 = 各 seed 中位数的中位数；"
        "粗扫/致密重合点（4096 KiB）逐 seed 先合并。",
        "",
        "## 图 1：L1 TLB 重填密度（refill-density.svg）",
        "",
        "![L1 dTLB refill 密度](refill-density.svg)",
        "",
        fig1_reading,
        "",
        "## 图 2：page table walk onset（walk-onset.svg）",
        "",
        "![dtlb walk 密度](walk-onset.svg)",
        "",
        fig2_reading,
        "",
        "## 图 3：延迟对照（latency-cycles.svg）",
        "",
        "![延迟与 cycles/load](latency-cycles.svg)",
        "",
        _FIG3_READING,
        "",
        "## 图 4：THP cohort 对照（thp-cohort.svg）",
        "",
        "![THP cohort 对照](thp-cohort.svg)",
        "",
        _FIG4_READING,
        "",
        "cohort 分级明细（`grade_thp_cohorts` 产出原样，可审计）：",
        "",
        *cohort_grading_lines(graded),
        "",
        final_heading,
        "",
        final_states,
        "",
        "## 没测到什么（边界）",
        "",
        _NOT_MEASURED,
        "",
        "## 复算",
        "",
        _REPRODUCE,
        "",
    ]
    if skipped_points:
        lines += [
            "",
            "## 数据局限（降级跳过点，MB-07 披露）",
            "",
            "以下 (run, buffer, seed, field) 因 metric 契约降级未进曲线。"
            "本报告**未对缺点数据执行重判**：终态表与图读法均为 2026-09-28 "
            "冻结历史终态的引用；被标注「当前曲线不支持」的区间与读法，"
            "在完整网格恢复前不应引用。",
            "",
        ]
        lines += [
            f"- {entry['run']} b{entry['buffer_kb']}K seed={entry['seed']} "
            f"{entry['field']}" for entry in skipped_points
        ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="analysis.tlb_figures",
                                   description=__doc__.splitlines()[0])
    parser.add_argument("--runs-root", required=True,
                        help="run 数据根目录（须含钉死名单的 4 个 run）")
    parser.add_argument("--out", required=True, help="输出目录（4 个 SVG + report.md）")
    args = parser.parse_args(argv)
    try:
        scan_groups, thp_groups = load_campaign(Path(args.runs_root))
        graded = grade_thp_cohorts(thp_groups)
        audit: dict = {}
        figures = build_figures(scan_groups, graded, audit=audit)
        skipped = audit.get("skipped_points", [])
        if skipped:
            # MB-07：部分缺点 = CLI 成功 + 显式披露（stderr 结构化 + 报告段）
            print(
                f"note: {len(skipped)} degraded point(s) skipped from "
                f"curves: {skipped}",
                file=sys.stderr,
            )
        # MB-07 收口复核：缺点数据下按当前曲线实际覆盖评估冻结判定区间的
        # 支持度（knee [480,4096] KiB / walk onset [10240,12288] KiB），
        # 报告内不受支持的区间/读法就地标注，禁止历史终态冒充本次重判。
        claim_support = None
        if skipped:
            refill_pts = curve_from_groups(scan_groups, _F_REFILL)
            walk_pts = curve_from_groups(scan_groups, _F_WALK)
            claim_support = {
                "refill_knee": any(
                    _KNEE_REGION_KB[0] <= kb <= _KNEE_REGION_KB[1]
                    for kb, _ in refill_pts),
                "walk_onset": any(
                    _WALK_ONSET_REGION_KB[0] <= kb <= _WALK_ONSET_REGION_KB[1]
                    for kb, _ in walk_pts),
            }
        report = build_report(graded, skipped_points=skipped,
                              claim_support=claim_support)
    except (TlbError, FileNotFoundError, ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, svg in figures.items():
        (out / name).write_text(svg, encoding="utf-8")
        print(f"chart:  {out / name}")
    (out / "report.md").write_text(report, encoding="utf-8")
    print(f"report: {out / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
