# 自有cache marker实现计划

目的与冻结判据：`docs/design/2026-10-13-rob-cache-marker.md`。

1. actual C producer及N0代码/八格顺序/架构marker tests先RED再GREEN；不依赖PMU。
2. consumer原样记录/严格类型/全覆盖/原结果及校准Type7判据；不同模式原失败不晋升。
3. 两NDK构建、actual native plans、独立解码；Git source/build/launch分离。
4. 实际plan→正式driver→writer→immutable source raw回读；缺失/重复/乱序/原结果/PFN/阈值来源等攻击，模拟timer与设备实测分列。
5. live ownership/unfinished/environment检查后串行6process，无全局环境改动，首技术失败停，校准及每窗原值完整保留。
6. 第二算术/raw SHA复核，qualified才另设计filler；结果/下一触发及MEMORY扩展note及时沉淀。
