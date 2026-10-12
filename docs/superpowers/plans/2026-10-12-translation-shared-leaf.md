# Shared leaf能力 Implementation Plan

## 本次任务的目的（给人类看）

验证真实memfd alias能否沿45指令leaf路线被安全观测。

**Goal:** 三进程shared身份能力，NOT_EXCITED不重试。
**Architecture:** 专门shared producer+typed wrapper/raw/driver，复用immutable BPF emitter与旧leaf合同。
**Tech Stack:** C/NDK27.2/API34/Python/adb，primary串行。

- [x] 实际producer缺失RED，shared mapping/plan/consumer canonical身份与未激励反例GREEN；source commit。
- [x] 双NDK/actual plan/source/bytecode绑定，新旧observer完整生产链回归；冻结launch后所有前置门过再3进程。
- [x] raw独立第二算术及匿名证据完整入库，更新状态/open-items/记忆；performance/steady CONT/HPA仍未认证。
