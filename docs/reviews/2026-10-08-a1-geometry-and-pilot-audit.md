# A1 几何修复、pilot吸收与交接更新（2026-10-08）

## 本次任务的目的（给人类看）

把真机pilot暴露的几何问题转成可复现的软件修复；保存有用的探索证据，明确不能继承的标定资格；让上板Agent下一次从小规模几何验证开始。用户已同意上一轮预约内对齐建议并要求继续，本轮不连接手机、不推远程。

**裁定：本轮软件几何修复自验通过；正式矩阵仍待新二进制的设备几何资格与专用标定冻结。原v1.9软件消费/集成结论保持其验证范围，本版任务书v1.9.1补充采集可达性保障，不修改H候选、正式矩阵或阈值规则。** 本轮没有第二位独立评审，不声称双评审或真机几何已通过。

**代码提交：r2 `49da3e7`。** 全量测试在提交前对相同代码内容执行，验证运行时代码/配置SHA与已提交文件逐项一致；文档与证据提交在其后，不改变验证代码。

## 1. 旧设备记录的只读复核

来源是m0b工作区 `data/public/runs/` 下六个目录；原记录/raw/manifest均未移动、修改或代提交。派生审计 `docs/reviews/evidence/2026-10-08-a1-geometry/pilot-audit.json` 给出逐run文件SHA、记录source/binary及domain/purity计数。

| run时间戳/后缀 | records | 实际状态/谱系 |
|---|---:|---|
| 081235Z anchor | 2 ok | 前锚点，binary 1e03a658…；旧record无experiment_id |
| 081255Z g03-empty | 1 failed | parse-error，10份raw保留 |
| 082002Z g03-empty | 1 ok | binary 36aa9228…，source b0f287f/dirty=true |
| 082019Z g03-noconflict | 0 | 未完成run：空records、raw子目录、无manifest |
| 082818Z g03-noconflict | 4 ok | binary 36aa9228…，clean6f433e3 |
| 082848Z anchor | 2 ok | 后锚点，binary 36aa9228…，clean6f433e3 |

因此“成功选取9/9、90个进程观测”成立，但完整尝试另有失败与未完成run。现存100份raw stdout/stderr复合工件按 `runner/artifacts.py` 同款分隔字节重算SHA全部匹配；摘要证明保存字节一致，不替代设备真实性/资格证明。

五条tlb-set记录共50个样本，全部 `set_domain=multi-region`；旧 `domain_consistent=false` 混入了域内VA变动，不能据此命名实际混域。当前 `runner/engine.py` 的domain_keys判定已与逐进程VA审计分开，不重写旧flag。

14/50样本purity=0（空窗6/10、noconflict8/40）。`probes/cache-mem/ptr_chase.cpp` 检查整个区域池而非仅目标链，不能断言每个实际目标链都跨窗；但当前 `analysis/sm8650_tlb_a1_contract.py` 对全部scope要求purity=1，所以这些记录不合正式几何资格。

锚点−0.6%/−0.8%只作描述，跨binary不能当同源夹块通过。空窗/scatter的L2 refill中位0与集中选址每轮8.0/6.0可作探索性对照响应，不能换算ways或确定H模型。旧run经当前 `analysis/sm8650_tlb_a1_freeze.py` 实际回读，首先命名拒绝 `calibration floor identity mismatch`；另有旧realized缺descriptor、dirty source及r10/r40不匹配专用r20输入。旧数据不晋升、不补写、不选择性裁剪。

## 2. 根因与修复

旧生产预约从任意mmap基址开始，四个64MiB池相对起点为k×256MiB+k×8页。池长小于256MiB并不保证池不跨256MiB边界，接近窗口尾部必跨窗。

`scripts/reproduce_tlb_region_boundary_20261008.py` 直接提取生产预约块，只替换系统调用返回地址，不重写布局算法。旧实现在offset_pages=65535稳定触发 `vpn-hi-impure`、退出1（预期RED）。修复后同一脚本通过全部65536页偏移×{2,4,16}区域，共196608组合，mprotect范围均在自有预约内。

新增共享 `probes/common/tlb_set_layout.h`：保留一个窗口的最坏对齐余量，在自有预约内取256MiB对齐起点，保留历史相对偏移/池余数分配；校验区域数、池容量、尺寸/地址溢出和范围。`probes/cache-mem/ptr_chase.cpp` 采用该布局，仍按原预约起点/全长munmap。映射失败的single-region-fallback继续显式披露并被正式消费者拒绝，不借修复放宽门。

输出purity仍独立由实际池起止地址计算；不新增record字段。新头纳入 `analysis/sm8650_tlb_a1_freeze.py` 的CODE_PATHS，漏登记反例先RED，再验证头文件内容漂移使冻结工件被拒。旧二进制和标定不继承。

`probes/tests/tlb_set_layout_golden.cpp` 覆盖全部页偏移、纯净/不同hi、预约范围、相对偏移、余数/极限池、短预约和溢出；真实宿主PROT_NONE预约及H×target×scope×W采集配额/实际目标索引/scatter不同set也通过。`probes/tests/tlb_set_collect_golden.cpp` 改用共享布局，完整长度munmap，消除手写布局与生产分叉。均不执行PMU。

## 3. 验证与边界

| 检查 | 本轮实际结果 |
|---|---|
| 生产块确定性边界反例 | RED退出1；修复后196608组合GREEN退出0 |
| 共享布局单独严格编译 | c++17 -O2 -Wall -Wextra -Werror，全部断言通过 |
| macOS标准preset构建/CTest | 通过，21/21（新增布局黄金测试） |
| analysis全量 | 250/250，含新冻结依赖测试 |
| runner全量 | 198/198；首次受沙箱私有测试锁写权限阻断，获写权限后完整重跑通过 |
| 新资格配置真实plan | 12cases、每case2reps、CPU7 |
| 新资格配置真实producer→写盘→审计回读 | 12条ok/24合成观测，几何/统计/完整身份与同源regime通过；交接原样审计代码块正例通过、purity反例命名拒绝 |
| 原软件出口复现 | 正式128条/1280合成观测、独立两标定、缺失/重复/冲突拒绝、置换不变通过 |
| 旧数据/图表 | 51runs/295records规范化统计与cohort相等；四SVG+报告5/5字节相等 |

这些分别是纯整数、宿主mmap和合成外部I/O证据。没有执行NDK构建、adb、SM8650进程或目标PMU。新增冒烟24进程也只是合成生产链验证，其设备执行仍待上板Agent。

证据目录 `docs/reviews/evidence/2026-10-08-a1-geometry/`：RED/GREEN、完整analysis/runner/CTest日志、`integration.json`、`smoke-producer.json`、`pilot-audit.json`；`verification-manifest.json`记录验证源码/配置与证据SHA。RED日志用于证明旧缺陷，不计最终通过。

复现（r2根目录；宿主环境）：

```bash
PY=/Users/michaelyao/workspace/cpu-uarch-explorer/.venv/bin/python
PYTHONDONTWRITEBYTECODE=1 "$PY" scripts/reproduce_tlb_region_boundary_20261008.py --tree .
cmake --preset macos-arm64-release
cmake --build --preset macos-arm64-release
ctest --preset macos-arm64-release
PYTHONDONTWRITEBYTECODE=1 "$PY" -m unittest discover -s analysis/tests -t .
PYTHONDONTWRITEBYTECODE=1 "$PY" -m unittest discover -s runner/tests -t .
PYTHONDONTWRITEBYTECODE=1 "$PY" scripts/verify_a1_software_exit_20261008.py --tree . --out /tmp/a1-geometry-software-exit.json
```

## 4. 交接与下一步

当前执行包 `docs/runbooks/2026-10-08-sm8650-a1-integrated-handoff.md` v2：新增pilot吸收/限制、独立几何资格、可执行审计命令、“冻结成功”和48/48/32定义。旧 `docs/runbooks/2026-10-07-sm8650-tlb-pilot-kickoff.md` 只加历史替代提示；任务书 `docs/tasks/2026-09-30-sm8650-tlb-hierarchy-r2.md` v1.9.1同步几何和路径索引。

上板Agent从新r2重编部署→12cases/24进程几何资格→同一新binary的前锚点/专用floor与scatter/后锚点→freeze成功→正式48/48/32×10→adjudicate。失败/输入错误/STOP停块回传，不随机筛纯样本。目标资格、Linux路径及旧数据归档责任登记 `docs/open-items.md` 的BOARD-A1-GEOMETRY-20261008；Android preset缺口和A3/ROB等保持原归属。

本轮只提交自有r2文件与派生审计，不移动/代提交m0b run、不改main他人草稿、不推远程。m0b使命与分支生命周期不变，r2继续承接设备与科学终态。
