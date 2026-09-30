# SPDX-License-Identifier: Apache-2.0
"""报告层测试：合成 run fixture（不依赖真机数据）守三件事：
1. failed 记录被隔离、不混入图表；
2. 报告含测量纪律 §7 的全部强制元信息项；
3. SVG 是良构 XML 且含全部控制组系列。

TestChartAnnotations 钉 chart.py 泛化（2026-09-30，TLB 战役图表需求）：
默认参数输出与泛化前逐字节一致（sha256 钉 + 显式默认零差异）、
shaded/vlines 几何与分层（画在数据线之下）、注解文本 XML 转义、
越界注解 fail-closed。
"""

import hashlib
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from analysis.chart import latency_svg
from analysis.cli import main as cli_main
from analysis.load import load_run
from analysis.report import build_report


def _record(control_value: str, buffer_kb: int, median: float, status: str = "ok") -> dict:
    r = {
        "schema_version": "2.0",
        "run_id": "123e4567-e89b-42d3-a456-426614174000",
        "timestamp": "2026-09-24T15:00:00Z",
        "status": status,
        "target": {"os": "darwin", "isa": "aarch64", "execution_kind": "native",
                   "executor": "native", "target_id": "t-01", "cpu_profile": "test-soc"},
        "probe": {"name": "ptr_chase", "protocol_version": "1.0",
                  "implementation_id": "portable",
                  "git": {"commit": "abc123", "dirty": False},
                  "artifact": {"sha256": "0" * 64}},
        "environment": {"control": {"mechanism": "qos", "value": control_value}},
        "params": {"buffer_kb": buffer_kb},
        "metrics": [],
        "evidence": {"provenance": "MEASURED"},
    }
    if status == "ok":
        r["metrics"] = [{"name": "latency_ns", "value": median, "unit": "ns",
                         "repetitions": 5,
                         "statistics": {"median": median, "min": median, "max": median,
                                        "p25": median, "p75": median}}]
    else:
        r["failure"] = {"reason": "probe-exit-1"}
    return r


def _make_run(d: Path) -> Path:
    run = d / "run"
    run.mkdir()
    records = (
        [_record("default", kb, v) for kb, v in [(32, 0.8), (256, 7.0), (262144, 120.0)]]
        + [_record("background", kb, v) for kb, v in [(32, 1.4), (256, 9.2), (262144, 190.0)]]
        + [_record("default", 64, 0.0, status="failed")]
    )
    with open(run / "records.jsonl", "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    (run / "run-manifest.json").write_text(json.dumps(
        {"experiment_id": "test-sweep", "target": {}, "summary": {"total": 7}}))
    return run


class TestLoad(unittest.TestCase):
    def test_ok_and_failed_separated(self):
        with tempfile.TemporaryDirectory() as d:
            run = load_run(_make_run(Path(d)))
            self.assertEqual(len(run.ok_records), 6)
            self.assertEqual(len(run.failed_records), 1)

    def test_missing_records_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                load_run(d)


class TestReport(unittest.TestCase):
    def test_mandatory_metadata_and_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            run = load_run(_make_run(Path(d)))
            md = build_report(run, "latency.svg")
        for needle in ["温度口径", "页策略", "重复次数", "置信度", "证据等级", "测量日期",
                       "qos=default", "qos=background", "probe-exit-1", "失败记录"]:
            self.assertIn(needle, md, f"报告缺少 {needle}")
        # 台阶推断：两组都应检出 32KB→256KB 以上的跳变
        self.assertIn("层级台阶", md)
        self.assertIn("×8.8", md)  # 0.8→7.0

    def test_empty_series_rejected(self):
        with self.assertRaises(ValueError):
            latency_svg({}, "t")


class TestChart(unittest.TestCase):
    def test_svg_wellformed_and_has_all_series(self):
        svg = latency_svg({"qos=default": [(32, 0.8), (256, 7.0)],
                           "qos=background": [(32, 1.4), (256, 9.2)]}, "测试标题")
        root = ET.fromstring(svg)  # 非良构会抛异常
        self.assertTrue(root.tag.endswith("svg"))
        self.assertIn("qos=default", svg)
        self.assertIn("qos=background", svg)

    def test_xml_injection_escaped(self):
        svg = latency_svg({"<script>": [(32, 1.0), (64, 2.0)]}, "t")
        self.assertNotIn("<script>", svg)
        ET.fromstring(svg)


class TestChartAnnotations(unittest.TestCase):
    SERIES = {"qos=default": [(32, 0.8), (256, 7.0)],
              "qos=background": [(32, 1.4), (256, 9.2)]}

    def test_default_output_byte_pin(self):
        # 泛化前现状输出的 sha256（2026-09-30 捕获于 main 9316853）；默认
        # 参数下必须与现状逐字节一致——改动默认渲染须显式更新本钉。
        svg = latency_svg(self.SERIES, "测试标题")
        self.assertEqual(
            hashlib.sha256(svg.encode("utf-8")).hexdigest(),
            "77851a709b0ff9c3951c07b1e54301336239a065b1d4d86d510ed3caf0041681")

    def test_explicit_defaults_zero_diff(self):
        base = latency_svg(self.SERIES, "测试标题")
        explicit = latency_svg(self.SERIES, "测试标题",
                               x_label="buffer size（log2，每格一倍）",
                               y_label="latency_ns（log2）",
                               shaded=[], vlines=[])
        self.assertEqual(base, explicit)

    def test_custom_axis_labels(self):
        svg = latency_svg({"s": [(128, 1.0), (256, 2.0)]}, "t",
                          x_label="buffer（log2）", y_label="R/1k（log2）")
        self.assertIn("buffer（log2）", svg)
        self.assertIn("R/1k（log2）", svg)
        self.assertNotIn("latency_ns（log2）", svg)

    def test_shaded_band_geometry_and_layering(self):
        svg = latency_svg({"s": [(128, 1.0), (32768, 100.0)]}, "t",
                          shaded=[(256, 4096, "Q1 转折区 [120,1024] 页")])
        # X 映射钉：80 + (log2(kb)-7)/8×750 → X(256)=173.75、X(4096)=548.75
        self.assertIn('<rect x="173.8" y="40" width="375.0" height="390" '
                      'fill="#2563eb" fill-opacity="0.08"/>', svg)
        self.assertIn("Q1 转折区 [120,1024] 页", svg)
        # 底色块与标注都画在数据线之下
        self.assertLess(svg.index("fill-opacity"), svg.index("<polyline"))
        ET.fromstring(svg)

    def test_vline_geometry_right_side(self):
        svg = latency_svg({"s": [(128, 1.0), (32768, 100.0)]}, "t",
                          vlines=[(8192, "MMUTC 2048 项")])
        # X(8192)=642.5 > 绘图区中线 455 → 标注 anchor=end 在线左侧（避开图例）
        self.assertIn('<line x1="642.5" y1="40" x2="642.5" y2="430" '
                      'stroke="#dc2626" stroke-width="1" stroke-dasharray="4 3"/>', svg)
        self.assertIn('x="637.5" y="54" text-anchor="end"', svg)
        self.assertIn("MMUTC 2048 项", svg)
        self.assertLess(svg.index("stroke-dasharray"), svg.index("<polyline"))
        ET.fromstring(svg)

    def test_vline_geometry_left_side(self):
        svg = latency_svg({"s": [(128, 1.0), (32768, 100.0)]}, "t",
                          vlines=[(256, "L")])
        # X(256)=173.75 ≤ 中线 → 标注 anchor=start 在线右侧
        self.assertIn('x="178.8" y="54" text-anchor="start"', svg)

    def test_annotation_text_xml_escaped(self):
        svg = latency_svg({"s": [(128, 1.0), (256, 2.0)]}, "t",
                          x_label="<x>", y_label="&y",
                          shaded=[(128, 256, "a<b")], vlines=[(192, "c&d")])
        self.assertNotIn("<x>", svg)
        ET.fromstring(svg)

    def test_empty_series_rejected_with_annotations(self):
        with self.assertRaises(ValueError):
            latency_svg({}, "t", shaded=[(1, 2, "x")], vlines=[(1, "y")])

    def test_shaded_outside_range_rejected(self):
        with self.assertRaises(ValueError):
            latency_svg({"s": [(128, 1.0), (256, 2.0)]}, "t",
                        shaded=[(1024, 2048, "外")])

    def test_vline_outside_range_rejected(self):
        with self.assertRaises(ValueError):
            latency_svg({"s": [(128, 1.0), (256, 2.0)]}, "t",
                        vlines=[(4096, "外")])


class TestCli(unittest.TestCase):
    def test_report_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            run = _make_run(Path(d))
            self.assertEqual(cli_main(["report", "--run", str(run)]), 0)
            self.assertTrue((run / "report.md").is_file())
            self.assertTrue((run / "latency.svg").is_file())
            # 重复执行幂等
            self.assertEqual(cli_main(["report", "--run", str(run)]), 0)


if __name__ == "__main__":
    unittest.main()
