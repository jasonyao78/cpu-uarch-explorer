# SPDX-License-Identifier: Apache-2.0
"""平台能力采集器：cache 拓扑 + cpufreq 事实（capability discovery 层，ADR-0006）。

设计讨论结论（2026-09-25，应用户提议落定）：探测不到的平台零损失
（available:false 如实入档）；探测到的平台获得"测量校验准绳"——
sysfs 的 L1/L2/L3 容量与组相联是真值，未来报告层可自动对照实测台阶
位置（Xeon 首测已人工完成一次对照，设计文档 §11）。

实现形态选择：Python 采集器经执行器通道读 sysfs，而非 C 探针——
sysfs 是文件系统事实不需要二进制；走 executor 通道使同一代码跨
transport（local/ssh 今天可用，未来 adb shell 同码）。产物为
capability-manifest 记录（runner/schema/capability-manifest.schema.json），
入库 data/public/capabilities/<target_id>-<stamp>.json。

口径声明：cache 拓扑取 cpu0（Linux 同构核代表值；异构 SoC 的 per-cluster
差异（GB10/Android big.LITTLE）为已知局限，接入异构平台时扩展为
representative-cpus 列表采集）。
"""

from __future__ import annotations

from . import capabilities

__all__ = ["capabilities"]
