# SPDX-License-Identifier: Apache-2.0
"""cpu-uarch-explorer runner: 组合式实验编排（ADR-0006 最小纵向闭环）。

层次：spec/plan（确定性计划）→ adapters（Probe ABI）→ executor（执行）
→ artifacts（原始样本）→ statistics → records（run-record v2 落盘）。
stdlib only（ADR-0003：双端零依赖精神）；schema 校验属开发期动作。
"""
