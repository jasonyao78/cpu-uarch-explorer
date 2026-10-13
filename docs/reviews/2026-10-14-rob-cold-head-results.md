# 最老cold load资格：长延迟与标记通过，缓存差模型被推翻

结论：**整批原资格不通过（COLD_HEAD_NOT_QUALIFIED）**；16/16、4096/4096正式、16384/16384warm、invalid0，own metadata/FD/realized head pointer/内容链/PFN/ISA/架构/恢复全部接受。四个cold issue配置的marker-observable与strict I-cache门通过，全部冷热长延迟门通过；五个cache/taps cell的L1D/L2D差值预测门失败，原门不更改。

branch `codex/sm8650-tlb-hierarchy-r2`；source `3aefd2802f282a150b4f5a23ed62e6957c1091e0`；build/actual launch `6c0888c37654f7f1024ed32f28757bb6b99921bb`；binary `3b7477fdbfefa089c7c7e23bf40483da936a52fa29785cd52fd4294c2ccb71a1`；raw `data/private/20261013T192211Z-rob-cold-head`。原始完整轨迹SHA与两palette实际事件标签校验，无FP、head1/2 LDR真实依赖、0/1值与返回内容链全部审核。

| epoch | heads | palette | cell | cold−hot cycle median | ΔL1D/ΔL2D mean（cache） | 失败门 |
|---|---|---|---|---|---|---|
| 0 | 1 | issue | pre-nop | 281.0 | — |  |
| 0 | 1 | issue | pre-taps | 287.0 | — |  |
| 0 | 1 | issue | post-nop | 315.0 | — |  |
| 0 | 1 | issue | post-taps | 278.5 | — |  |
| 0 | 1 | cache | pre-nop | 278.0 | 1 / 1 |  |
| 0 | 1 | cache | pre-taps | 273.0 | -0.062 / 1 | pre-taps-cache |
| 0 | 1 | cache | post-nop | 320.0 | 1 / 1 |  |
| 0 | 1 | cache | post-taps | 262.5 | 0.094 / 1 | post-taps-cache |
| 0 | 2 | issue | pre-nop | 257.5 | — |  |
| 0 | 2 | issue | pre-taps | 284.0 | — |  |
| 0 | 2 | issue | post-nop | 299.0 | — |  |
| 0 | 2 | issue | post-taps | 271.0 | — |  |
| 0 | 2 | cache | pre-nop | 358.0 | 2 / 1.875 |  |
| 0 | 2 | cache | pre-taps | 371.0 | 2.219 / 1.812 |  |
| 0 | 2 | cache | post-nop | 360.0 | 2 / 1.844 |  |
| 0 | 2 | cache | post-taps | 363.5 | 2.125 / 1.781 |  |
| 1 | 1 | issue | pre-nop | 229.0 | — |  |
| 1 | 1 | issue | pre-taps | 230.5 | — |  |
| 1 | 1 | issue | post-nop | 226.5 | — |  |
| 1 | 1 | issue | post-taps | 235.0 | — |  |
| 1 | 1 | cache | pre-nop | 309.0 | 0.938 / 1 |  |
| 1 | 1 | cache | pre-taps | 358.0 | 1.812 / 1 | pre-taps-cache |
| 1 | 1 | cache | post-nop | 333.5 | 0.938 / 1 |  |
| 1 | 1 | cache | post-taps | 316.0 | 1.844 / 1 | post-taps-cache |
| 1 | 2 | issue | pre-nop | 353.5 | — |  |
| 1 | 2 | issue | pre-taps | 344.0 | — |  |
| 1 | 2 | issue | post-nop | 384.5 | — |  |
| 1 | 2 | issue | post-taps | 379.0 | — |  |
| 1 | 2 | cache | pre-nop | 466.5 | 2.188 / 1.781 |  |
| 1 | 2 | cache | pre-taps | 435.0 | 2.562 / 1.812 | pre-taps-cache |
| 1 | 2 | cache | post-nop | 404.0 | 2.156 / 1.844 |  |
| 1 | 2 | cache | post-taps | 499.5 | 2.375 / 1.844 |  |

缓存事实：head1 cache/nop的差值接近1/1；taps在e0 L1D差接近0、e1接近1.8，但L2D均1。head2 nop差接近2，taps有一个L1D略超2.5。不能把head数量直接等同整个带8near/8far标记窗口的L1D差。标记原始计数、所有negative/极端/供给门完整保留；结果不是“冷head没激励”或“ROB无容量”。

当前设计的冷热分别fresh process，其他物理页面/PFN及L1D映射可不同；head/near/out/metadata常在页offset0，缓存组交互是可检验的解释，未证明唯一原因。下一版预注册：冷热同process/sameVA/PFN交错；head页内offset独立对照0/1024，真实地址和值路径注册，避免跨process几何差并直接推翻/支持冲突解释。新观测不回救原本批。

距目标：最老long load触发、near/far、owned观察器、完整重复filler粗窗口均已有正证据，但资源/分配单位及精确ROB仍需这组缓存/生命周期反证。第三方384未被当真值；L1i48/d96已测、共享L2规格2048/256×8已匹配，与独立leaf/selector边界分列。所有PMU恢复0，未操作main/remote。
