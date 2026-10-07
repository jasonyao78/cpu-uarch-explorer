# SPDX-License-Identifier: Apache-2.0
"""ptr_chase adapter：指针追逐内存延迟探针（probes/cache-mem/ptr_chase.cpp）。

Probe ABI（与源码头部注释一致）：
  argv:  -b buffer_kb -s stride_bytes -n loads -w warmup [-S seed]
         [-B|-h|-H|-T] [--pmu-event label:type:config]...
  stdout: buffer_kb=.. .. latency_ns=.. warmup_loads=..
          warmup_passes_effective=.. warmup_state=.. page_policy=.. page_kb=..
          page_policy_actual_before/after=.. anon_huge_kb_before/after=..
          page_backing_endpoints_equal=1（两端观测一致，不代表连续观测）
          vma_base=0x…（建链缓冲区起始 VA，ASLR 布局观测，路线 A）
          seed=N（链洗牌种子，默认 42；访问序列是实验变量，必须入档）
  退出码: 0 成功 / 1 输入或环境错误 / 2 能力不支持（hugepage 无平台能力或
          strict 模式缺页池；fallback 非 strict 模式下成功但标注 fallback-4k）

measurement-discipline §2：请求页策略与实际 backing 必须分字段保存；
page_policy 随 metric 入档（requested/actual 双记录原则）。新输出还在
warmup 后/测量前与 timed/PMU 窗后做端点审计；parser 继续接受旧捕获。
"""

from __future__ import annotations

import re
from typing import Any

from runner.errors import ParseError

from .base import parse_key_value_lines, require_finite_number

_PMU_LABEL_RE = re.compile(r"^[a-z0-9_]+$")
_VMA_BASE_RE = re.compile(r"^0x[0-9a-f]+$")
_PMU_SUFFIXES = (
    "_time_enabled_ns", "_time_running_ns", "_config", "_count", "_type",
)
_PAGE_BACKINGS = ("platform-default", "base", "thp", "mixed", "hugetlb-2m")


def _binary_flag(params: dict[str, Any], name: str) -> int:
    raw = params.get(name, 0)
    if type(raw) is int and raw in (0, 1):
        return raw
    if type(raw) is str and raw in ("0", "1"):
        return int(raw)
    raise ParseError(f"{name} must be 0 or 1, got {raw!r}")


def _pmu_events(params: dict[str, Any]) -> list[dict[str, int | str]]:
    raw = params.get("pmu_events", [])
    if not isinstance(raw, list):
        raise ParseError(f"pmu_events must be a list, got {raw!r}")
    normalized: list[dict[str, int | str]] = []
    labels: set[str] = set()
    for index, event in enumerate(raw):
        if not isinstance(event, dict) or set(event) != {"name", "type", "config"}:
            raise ParseError(f"pmu_events[{index}] must contain exactly name/type/config")
        label = event["name"]
        event_type = event["type"]
        config = event["config"]
        if not isinstance(label, str) or not _PMU_LABEL_RE.fullmatch(label):
            raise ParseError(f"pmu_events[{index}].name is unsafe: {label!r}")
        if label in labels:
            raise ParseError(f"pmu_events has duplicate name {label!r}")
        if type(event_type) is not int or not 0 <= event_type <= (1 << 32) - 1:
            raise ParseError(f"pmu_events[{index}].type is not uint32: {event_type!r}")
        if type(config) is not int or not 0 <= config <= (1 << 64) - 1:
            raise ParseError(f"pmu_events[{index}].config is not uint64: {config!r}")
        labels.add(label)
        normalized.append({"name": label, "type": event_type, "config": config})
    return normalized


def _require_uint(fields: dict[str, str], key: str, maximum: int) -> int:
    raw = fields.get(key)
    if raw is None or not raw.isdigit():
        raise ParseError(f"field {key!r} must be an unsigned integer: {raw!r}")
    value = int(raw)
    if value > maximum:
        raise ParseError(f"field {key!r} exceeds {maximum}: {raw!r}")
    return value


class PtrChaseAdapter:
    probe_name = "ptr_chase"
    protocol_version = "1.2"
    implementation_id = "portable"

    # M0-4b：tlb_set 形状的必需参数（探针 argv 真实消费；缺一即 ParseError，
    # fail-closed——不让半套参数悄悄退化成别的模式）
    _SET_MODE_REQUIRED = ("set_hypothesis", "set_target", "set_window")
    _SET_MODE_OPTIONAL = ("set_target2", "set_rounds", "set_pool_pages",
                          "set_filler_pages", "set_regions")

    def build_argv(self, params: dict[str, Any]) -> list[str]:
        """参数 dict → probe argv。缺参数/类型错误抛 ParseError（plan 期已校验，
        此处是最后一道防线）。hugepage 非 0 时加 -h（fallback 允许）；
        thp 非 0 时加 -T；base_pages 非 0 时加 -B；三类页请求互斥。
        M0-4b：含 set_window 参数 → tlb_set 模式 argv（--tlb-set-mode 族），
        与 legacy chase argv 互斥（探针侧同样硬拒）。"""
        if "set_window" in params or "set_hypothesis" in params:
            return self._build_tlb_set_argv(params)
        return self._build_chase_argv(params)

    def _build_tlb_set_argv(self, params: dict[str, Any]) -> list[str]:
        for key in self._SET_MODE_REQUIRED:
            if key not in params:
                raise ParseError(
                    f"tlb-set mode requires param {key!r} "
                    f"(got {sorted(params)})")
        try:
            hypothesis = int(params["set_hypothesis"])
            target = int(params["set_target"])
            window = int(params["set_window"])
        except (TypeError, ValueError) as e:
            raise ParseError(f"tlb-set argv build failed: {e}")
        if not 1 <= hypothesis <= 4:
            raise ParseError(f"set_hypothesis must be 1..4: {hypothesis}")
        if not 0 <= target <= 255:
            raise ParseError(f"set_target must be 0..255: {target}")
        if window < 0:
            raise ParseError(f"set_window must be >= 0: {window}")
        argv = ["--tlb-set-mode",
                "--set-hypothesis", str(hypothesis),
                "--set-target", str(target),
                "--set-window", str(window)]
        if "set_target2" in params:
            target2 = int(params["set_target2"])
            if not 0 <= target2 <= 255:
                raise ParseError(f"set_target2 must be 0..255: {target2}")
            argv += ["--set-target2", str(target2)]
        for key, flag in (("set_rounds", "--set-rounds"),
                          ("set_pool_pages", "--set-pool-pages"),
                          ("set_filler_pages", "--set-filler"),
                          ("set_regions", "--set-regions")):
            if key in params:
                argv += [flag, str(int(params[key]))]
        if int(params.get("set_region_scope", -1)) != -1:
            argv += ["--set-region-scope", str(int(params["set_region_scope"]))]
        if int(params.get("set_nsets", 0)) > 0:
            argv += ["--set-nsets", str(int(params["set_nsets"]))]
        if _binary_flag(params, "set_scatter"):
            argv.append("--set-scatter")
        if "seed" in params:
            raw_seed = params["seed"]
            if type(raw_seed) is not int or raw_seed < 0 \
                    or raw_seed > (1 << 64) - 1:
                raise ParseError(f"seed must be a uint64 integer: {raw_seed!r}")
            argv.extend(["-S", str(raw_seed)])
        # tlb_set 强制 4K base 页：显式带 -B 与探针内部 madvise 口径一致
        argv.append("-B")
        for event in _pmu_events(params):
            argv.extend([
                "--pmu-event",
                f"{event['name']}:{event['type']}:{event['config']}",
            ])
        return argv

    def _build_chase_argv(self, params: dict[str, Any]) -> list[str]:
        try:
            buffer_kb = int(params["buffer_kb"])
            stride = int(params["stride"])
            loads = int(params["loads"])
            warmup = int(params["warmup"])
        except (KeyError, TypeError, ValueError) as e:
            raise ParseError(f"ptr_chase argv build failed: {e}")
        hugepage = _binary_flag(params, "hugepage")
        thp = _binary_flag(params, "thp")
        base_pages = _binary_flag(params, "base_pages")
        if hugepage + thp + base_pages > 1:
            raise ParseError("ptr_chase page policies are mutually exclusive")
        argv = ["-b", str(buffer_kb), "-s", str(stride),
                "-n", str(loads), "-w", str(warmup)]
        if "seed" in params:
            raw_seed = params["seed"]
            if type(raw_seed) is not int or raw_seed < 0 \
                    or raw_seed > (1 << 64) - 1:
                raise ParseError(f"seed must be a uint64 integer: {raw_seed!r}")
            argv.extend(["-S", str(raw_seed)])
        if hugepage:
            argv.append("-h")
        if thp:
            argv.append("-T")
        if base_pages:
            argv.append("-B")
        for event in _pmu_events(params):
            argv.extend([
                "--pmu-event",
                f"{event['name']}:{event['type']}:{event['config']}",
            ])
        return argv

    def parse_output(self, stdout: str, stderr: str,
                     expected: dict | None = None) -> list[dict[str, Any]]:
        """stdout key=value → metrics 列表。缺 latency_ns、非数值、nan/inf
        一律抛 ParseError（绝不编造数值，空 metrics + failure 是合法出路）。
        page_policy 存在时随 metric 入档（§2 显式标注纪律）。
        M0-4b：mode=tlbset 输出 → tlb_set 分支（无 latency_ns；metrics 为
        pmu.<label>.count 窗口差分均值 + 窗口有效性计数，事件集自描述）。
        MB-06：expected（plan case_params）提供时做 requested→realized
        一致性核验——探针自描述字段必须与请求的规范化参数一致，不符即
        ParseError（fail-closed，不让执行漂移混进证据）。"""
        fields = parse_key_value_lines(stdout)
        if not fields:
            raise ParseError(f"no key=value lines in probe output; stderr={stderr.strip()!r}")
        # PA-02 修订：解析形状由**请求**决定，不由输出自报决定——请求
        # tlb_set 而探针输出 legacy（无 mode=tlbset）= 执行漂移，fail-closed；
        # 请求 legacy 而输出 tlbset 同理。expected=None（旧调用）保持输出定形。
        if expected is not None:
            wants_set = "set_window" in expected or "set_hypothesis" in expected
            is_set = fields.get("mode") == "tlbset"
            if wants_set and not is_set:
                raise ParseError(
                    "descriptor shape mismatch: requested tlb_set but probe "
                    f"output has no mode=tlbset (mode={fields.get('mode')!r})")
            if is_set and not wants_set:
                raise ParseError(
                    "descriptor shape mismatch: probe reports mode=tlbset but "
                    "the case did not request a tlb_set shape")
        if fields.get("mode") == "tlbset":
            metrics = self._parse_tlb_set_output(fields, stderr)
            if expected is not None:
                self._check_tlb_set_descriptor(fields, expected)
            return metrics
        return self._parse_chase_output(fields, stderr)

    # MB-06/PA-02 descriptor 契约：探针自描述字段 ↔ plan 规范化参数名。
    # set_domain/set_active_regions/set_region_nodes 为 realized-only（预约/
    # 激励审计结果，非请求参数）——只由 parse_realized() 入档，不做一致性
    # 等值核验（single-region-fallback 是合法命名降级）。
    _TLB_SET_DESCRIPTOR_MAP = (
        ("set_hypothesis", "set_hypothesis"),
        ("set_target", "set_target"),
        ("set_target2", "set_target2"),
        ("set_window", "set_window"),
        ("set_rounds", "set_rounds"),
        ("set_pool_pages", "set_pool_pages"),
        ("set_filler_pages", "set_filler_pages"),
        ("set_regions", "set_regions"),
        ("scatter", "set_scatter"),
        ("set_region_scope", "set_region_scope"),
        ("set_nsets", "set_nsets"),
        ("seed", "seed"),
    )

    def parse_realized(self, stdout: str,
                       expected: dict | None = None) -> dict[str, Any]:
        """探针 realized 自描述域（PA-02/RPA-03：随结构化记录持久化，
        requested 与 realized 分开；每次进程解析阶段调用）。

        防御契约（评审反例驱动）：非法 token **拒绝而非丢弃**；有 expected
        时校验维数（== set_regions）、节点总和（== window×max(nsets,1)）、
        scope 隔离一致性、active_regions 与槽位一致性——任何违例 ParseError，
        由 engine 既有失败路径转成结构化 failure（不逃逸 ValueError）。"""
        fields = parse_key_value_lines(stdout)
        if fields.get("mode") != "tlbset":
            return {}
        realized: dict[str, Any] = {}
        for key in ("mode", "set_domain", "page_kb"):
            if key in fields:
                realized[key] = fields[key]
        if "set_region_vpn_hi" in fields:
            toks = str(fields["set_region_vpn_hi"]).split(",")
            if not all(t.isdigit() for t in toks):
                raise ParseError(
                    f"realized set_region_vpn_hi: invalid token in "
                    f"{fields['set_region_vpn_hi']!r}")
            realized["set_region_vpn_hi"] = [int(t) for t in toks]
        for key in ("set_region_vpn_hi_pure",):
            if key in fields:
                raw = fields[key]
                if raw not in ("0", "1"):
                    raise ParseError(f"realized {key}: must be 0/1, got {raw!r}")
                realized[key] = int(raw)
        for key in ("set_target_region_nodes", "set_t2_region_nodes"):
            if key not in fields:
                continue
            counts: list[int] = []
            for tok in str(fields[key]).split(","):
                if not tok.isdigit():   # 严格非负整数；非法 token 拒绝
                    raise ParseError(
                        f"realized {key}: invalid token {tok!r}")
                counts.append(int(tok))
            realized[key] = counts
        for key in ("set_hypothesis", "set_target", "set_window", "set_rounds",
                    "set_regions", "set_region_scope", "set_nsets",
                    "set_active_regions", "seed"):
            if key in fields:
                raw = fields[key]
                if not str(raw).lstrip("-").isdigit():
                    raise ParseError(f"realized {key}: not an integer: {raw!r}")
                realized[key] = int(raw)
        if expected is not None:
            self._check_realized_invariants(realized, expected)
        return realized

    def _check_realized_invariants(self, realized: dict[str, Any],
                                   expected: dict) -> None:
        regions = int(expected.get("set_regions", 4))
        for key in ("set_target_region_nodes", "set_t2_region_nodes"):
            if key in realized and len(realized[key]) != regions:
                raise ParseError(
                    f"realized {key}: dim {len(realized[key])} != "
                    f"set_regions {regions}")
        window = int(expected.get("set_window", 0))
        nsets = int(expected.get("set_nsets", 0))
        expected_sum = (window * (nsets if nsets > 0 else 1)
                        if window > 0 else 0)
        nodes = realized.get("set_target_region_nodes")
        if nodes is not None and sum(nodes) != expected_sum:
            raise ParseError(
                f"realized target node sum {sum(nodes)} != "
                f"window*nsets {expected_sum}")
        scope = int(expected.get("set_region_scope", -1))
        if nodes is not None and scope >= 0 and nodes[scope] != expected_sum:
            raise ParseError(
                f"realized scope isolation violated: slot[{scope}]="
                f"{nodes[scope]} != {expected_sum}")
        active = realized.get("set_active_regions")
        if active is not None and nodes is not None:
            actual = sum(1 for n in nodes if n > 0)
            if active != actual:
                raise ParseError(
                    f"realized set_active_regions {active} != nonzero "
                    f"slots {actual}")

    def _check_tlb_set_descriptor(self, fields: dict[str, str],
                                  expected: dict) -> None:
        """requested（expected case_params）→ realized（探针自描述）一致性。
        请求了但探针没报、或值不一致 = 执行漂移，fail-closed；请求的 PMU
        判据事件必须在输出中出现（缺关键事件 = 无可判读计数，命名拒绝）。"""
        for out_key, param_key in self._TLB_SET_DESCRIPTOR_MAP:
            if param_key in expected:
                if out_key not in fields:
                    raise ParseError(
                        f"tlb-set descriptor: probe did not report {out_key!r} "
                        f"for requested param {param_key!r}")
                if fields[out_key] != str(expected[param_key]):
                    raise ParseError(
                        f"tlb-set descriptor mismatch: {out_key}="
                        f"{fields[out_key]!r} != requested {param_key}="
                        f"{expected[param_key]!r}")
        requested = {e["name"] for e in _pmu_events(expected)}
        reported = {
            key[len("pmu_"):-len("_count")]
            for key in fields if key.startswith("pmu_") and key.endswith("_count")
        }
        missing_events = sorted(requested - reported)
        if missing_events:
            raise ParseError(
                f"tlb-set descriptor: requested PMU events missing from "
                f"probe output: {missing_events}")

    def _parse_tlb_set_output(self, fields: dict[str, str],
                              stderr: str) -> list[dict[str, Any]]:
        """tlb_set 模式：probe 段窗口差分均值（events/round）+ 有效性证据。

        事件集自描述（pmu_<label>_count 键）；至少一个事件必填，否则该
        窗口没有任何可判读的计数（fail-closed）。"""
        required = ("set_domain", "window_valid_rounds", "window_invalid_rounds",
                    "window_mux_rounds", "valid_rounds", "probe_ns")
        for key in required:
            if key not in fields:
                raise ParseError(f"tlb-set output missing {key!r}; stderr={stderr.strip()!r}")
        metrics: list[dict[str, Any]] = [
            {"name": "window_valid_rounds",
             "value": require_finite_number(fields, "window_valid_rounds"),
             "unit": "rounds"},
            {"name": "window_invalid_rounds",
             "value": require_finite_number(fields, "window_invalid_rounds"),
             "unit": "rounds"},
            {"name": "window_mux_rounds",
             "value": require_finite_number(fields, "window_mux_rounds"),
             "unit": "rounds"},
            {"name": "probe_latency_ns",
             "value": require_finite_number(fields, "probe_ns"),
             "unit": "ns"},
        ]
        n_events = 0
        for key, raw in fields.items():
            if not key.startswith("pmu_") or not key.endswith("_count"):
                continue
            label = key[len("pmu_"):-len("_count")]
            if not label:
                raise ParseError(f"tlb-set event label empty in key {key!r}")
            metrics.append({"name": f"pmu.{label}.count",
                            "value": require_finite_number(fields, key),
                            "unit": "events"})
            valid_key = f"pmu_{label}_valid_rounds"
            if valid_key in fields:
                metrics.append({
                    "name": f"pmu.{label}.valid_rounds",
                    "value": require_finite_number(fields, valid_key),
                    "unit": "rounds"})
            n_events += 1
        if n_events == 0:
            raise ParseError(
                f"tlb-set output has no pmu_<label>_count events; stderr={stderr.strip()!r}")
        return metrics

    def _parse_chase_output(self, fields: dict[str, str],
                            stderr: str) -> list[dict[str, Any]]:
        latency = require_finite_number(fields, "latency_ns")
        metric: dict[str, Any] = {"name": "latency_ns", "value": latency, "unit": "ns"}
        warmup_keys = {"warmup_loads", "warmup_passes_effective", "warmup_state"}
        present_warmup_keys = warmup_keys.intersection(fields)
        if present_warmup_keys:
            if present_warmup_keys != warmup_keys:
                missing = sorted(warmup_keys - present_warmup_keys)
                raise ParseError(f"incomplete warmup audit fields; missing {missing}")
            raw_loads = fields["warmup_loads"]
            if not raw_loads.isdigit():
                raise ParseError(f"warmup_loads must be a non-negative integer: {raw_loads!r}")
            warmup_loads = int(raw_loads)
            warmup_passes = require_finite_number(fields, "warmup_passes_effective")
            if warmup_passes < 0:
                raise ParseError(
                    f"warmup_passes_effective must be non-negative: {warmup_passes!r}"
                )
            warmup_state = fields["warmup_state"]
            if warmup_state not in ("warm", "cold-warm0"):
                raise ParseError(f"invalid warmup_state: {warmup_state!r}")
            expected_state = "cold-warm0" if warmup_loads == 0 else "warm"
            if warmup_state != expected_state:
                raise ParseError(
                    f"warmup_state {warmup_state!r} contradicts "
                    f"warmup_loads={warmup_loads}"
                )
            metric.update({
                "warmup_loads": warmup_loads,
                "warmup_passes_effective": warmup_passes,
                "warmup_state": warmup_state,
            })
        if "page_policy" in fields:
            metric["page_policy"] = fields["page_policy"]
        page_audit_keys = {
            "page_policy_requested", "page_policy_actual", "anon_huge_kb",
        }
        present_page_audit_keys = page_audit_keys.intersection(fields)
        if present_page_audit_keys:
            if present_page_audit_keys != page_audit_keys:
                missing = sorted(page_audit_keys - present_page_audit_keys)
                raise ParseError(f"incomplete page backing fields; missing {missing}")
            requested = fields["page_policy_requested"]
            if requested not in (
                "default", "base-madvise", "hugetlb-fallback", "hugetlb-strict",
                "thp-madvise",
            ):
                raise ParseError(f"invalid page_policy_requested: {requested!r}")
            actual = fields["page_policy_actual"]
            if actual not in _PAGE_BACKINGS:
                raise ParseError(f"invalid page_policy_actual: {actual!r}")
            raw_anon_huge_kb = fields["anon_huge_kb"]
            if not raw_anon_huge_kb.isdigit():
                raise ParseError(
                    f"anon_huge_kb must be a non-negative integer: {raw_anon_huge_kb!r}"
                )
            metric.update({
                "page_policy_requested": requested,
                "page_policy_actual": actual,
                "anon_huge_kb": int(raw_anon_huge_kb),
            })
        window_audit_keys = {
            "page_policy_actual_before", "page_policy_actual_after",
            "anon_huge_kb_before", "anon_huge_kb_after",
            "page_backing_endpoints_equal",
        }
        present_window_audit_keys = window_audit_keys.intersection(fields)
        if present_window_audit_keys:
            if present_window_audit_keys != window_audit_keys:
                missing = sorted(window_audit_keys - present_window_audit_keys)
                raise ParseError(
                    f"incomplete measurement-window page backing fields; missing {missing}"
                )
            if present_page_audit_keys != page_audit_keys:
                raise ParseError(
                    "measurement-window page backing fields require the legacy "
                    "requested/actual/anon_huge_kb fields"
                )
            before = fields["page_policy_actual_before"]
            after = fields["page_policy_actual_after"]
            if before not in _PAGE_BACKINGS or after not in _PAGE_BACKINGS:
                raise ParseError(
                    f"invalid measurement-window page backing: {before!r}/{after!r}"
                )
            raw_before_kb = fields["anon_huge_kb_before"]
            raw_after_kb = fields["anon_huge_kb_after"]
            if not raw_before_kb.isdigit() or not raw_after_kb.isdigit():
                raise ParseError(
                    "measurement-window anon_huge_kb values must be non-negative "
                    f"integers: {raw_before_kb!r}/{raw_after_kb!r}"
                )
            before_kb = int(raw_before_kb)
            after_kb = int(raw_after_kb)
            endpoints_equal = _require_uint(
                fields, "page_backing_endpoints_equal", 1,
            )
            if endpoints_equal != 1 or before != after or before_kb != after_kb:
                raise ParseError(
                    "successful ptr_chase output requires equal page-backing "
                    "observations at both measurement-window endpoints"
                )
            if before != metric["page_policy_actual"] \
                    or before_kb != metric["anon_huge_kb"]:
                raise ParseError(
                    "measurement-window page backing contradicts legacy summary fields"
                )
            metric.update({
                "page_policy_actual_before": before,
                "page_policy_actual_after": after,
                "anon_huge_kb_before": before_kb,
                "anon_huge_kb_after": after_kb,
                "page_backing_endpoints_equal": endpoints_equal,
            })
        if "page_kb" in fields:
            raw_page_kb = fields["page_kb"]
            if not raw_page_kb.isdigit():
                raise ParseError(f"page_kb must be a non-negative integer: {raw_page_kb!r}")
            metric["page_kb"] = int(raw_page_kb)
        labels: list[str] = []
        seen_labels: set[str] = set()
        for key in fields:
            if not key.startswith("pmu_"):
                continue
            label = None
            for suffix in _PMU_SUFFIXES:
                if key.endswith(suffix):
                    label = key[len("pmu_"):-len(suffix)]
                    break
            if label is None or not _PMU_LABEL_RE.fullmatch(label):
                raise ParseError(f"invalid PMU output field: {key!r}")
            if label not in seen_labels:
                seen_labels.add(label)
                labels.append(label)

        metrics = [metric]
        for label in labels:
            prefix = f"pmu_{label}_"
            event_type = _require_uint(fields, prefix + "type", (1 << 32) - 1)
            config = _require_uint(fields, prefix + "config", (1 << 64) - 1)
            count = _require_uint(fields, prefix + "count", (1 << 64) - 1)
            enabled = _require_uint(
                fields, prefix + "time_enabled_ns", (1 << 64) - 1,
            )
            running = _require_uint(
                fields, prefix + "time_running_ns", (1 << 64) - 1,
            )
            if running == 0:
                raise ParseError(f"PMU event {label!r} has zero running time")
            if running > enabled:
                raise ParseError(
                    f"PMU event {label!r} running time exceeds enabled time"
                )
            metrics.append({
                "name": f"pmu.{label}.count",
                "value": count,
                "unit": "events",
                "pmu_type": event_type,
                "pmu_config": config,
                "time_enabled_ns": enabled,
                "time_running_ns": running,
            })
        if "seed" in fields:
            # 链洗牌种子随每条 metric 入档（样本级溯源：地址相关预取/索引
            # 共振判别依赖逐样本 seed）。
            seed = _require_uint(fields, "seed", (1 << 64) - 1)
            for item in metrics:
                item["seed"] = seed
        if "vma_base" in fields:
            # 建链缓冲区起始 VA 随每条 metric 入档（SM8650 TLB 任务书路线 A：
            # order_seed 之外的布局观测依赖逐样本 VA；保持 hex 字符串不转
            # int，避免 reader 误当数值聚合）。
            vma_base = fields["vma_base"]
            if not _VMA_BASE_RE.fullmatch(vma_base):
                raise ParseError(
                    f"vma_base must be a lowercase hex address: {vma_base!r}")
            for item in metrics:
                item["vma_base"] = vma_base
        return metrics
