# SPDX-License-Identifier: Apache-2.0
"""analysis —— 报告层：消费 run 目录的 records.jsonl，生成 Markdown 报告
与 SVG 延迟曲线。

设计约束：
- stdlib 零依赖（与 runner 一致，ADR-0003 精神；图表为纯 SVG 生成，不引入
  matplotlib）；
- 报告遵守 measurement-discipline §7：每个数字携带温度口径 / 页策略 /
  重复次数与统计量 / 置信度 / 核型 / 证据等级 / 测量日期；
- 解释与事实分离：表格只陈述测量值，层级归属标注为"推断"并给出依据。
"""
