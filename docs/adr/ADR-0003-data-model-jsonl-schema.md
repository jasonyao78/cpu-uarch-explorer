# ADR-0003: 数据模型——JSONL 先行 + 定死 schema（元数据信封）

- 状态：已接受（2026-09-23）

## 背景

统一实验协议需要物理载体。历史教训：`cpu-cache-demo-code/sm8650-x4.txt` 无日期、无机型全称、无 kernel/编译器/commit 信息，导致数据不可复现、不可比对（sm8550 数据现已来源不可考）。核心需求是**统一 schema + 元数据信封**，而非某种存储技术本身。

## 决策

- 原始层唯一 source of truth：JSONL（每行一条 run 记录），追加写、流式可读、schema 可演进、C++/Python 双端零依赖。
- schema 第一天定死（`runner/schema/record.schema.json`），信封强制字段：run_id、timestamp、backend、device_code（匿名代号）、os/os_version/kernel、compiler/flags、probe_name、probe_git_commit、params、affinity/QoS 设置、metrics[]、evidence_level、raw_command、notes。
- 字段扁平化设计，未来 SQLite 汇总层（推迟）可无损映射，不嵌套大对象。
- SQLite/Parquet 现在不做：首次跨 run 分析需求出现时再引入由 JSONL 再生成的汇总层（YAGNI）。

## 后果

- 任何记录可回答"何时、在哪台设备、哪版代码、什么参数下测得"。
- 分析层延后不会造成返工：schema 已按可迁移设计。
