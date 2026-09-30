# ROB 探针骨架（对应《ROB微架构深度分析报告》§5）

目标平台：Android Linux arm64 / 高通 SM8650（仅测 Cortex-X4 核）。**本目录独立于本仓 CMake/runner 体系**（按项目边界声明：不做工程对接），用单条编译命令构建。

| 文件 | 对应章节 | 用途 |
|---|---|---|
| `rob_window_probe.c` | §5.4（E1/E2） | 窗口协议探针：mini-JIT 生成 [锚点 + N×填充 + 循环控制] 测量循环，7 个填充类别 × 2 锚点模式，入口对齐抖动，Linux perf RAW 事件组，逐轮 rawlog |

**版本**：v0.1（2026-09-29）初版。**TODO（骨架性质，采数前必须补齐）**：
- 无统计检验输出（只有 min/avg/max，置信区间由外层脚本算）；
- 无 DVFS 频率轨迹记录（PMU 通道不受频率影响，墙钟通道需要）；
- chase 回路完整性未校验（应断言调用后指针回到起点链上）；
- E0 五项（MOV 消除/NOP 发射/拆分因子基线/fsqrt 标定）尚无独立探针——`rob_window_probe` 的类别模式可覆盖部分（nop/add/movi/movr/fadd 流），但 E0 的"依赖链时延"测量需 v2 补 `-t chain` 模式；
- 混合类别（MIX-I+F / MIX-MOV，§5.5 末两行）未实现；
- 每 N 一个进程重启（chase 初始化每次 ~1s）——扫描 1024 点约 20 分钟纯初始化，v2 应改为进程内重建例程。

## 编译

**macOS 主机（M4）本机冒烟**（产物 Mach-O，仅验证生成码与流程；PMU 通道自动 n/a）：

```bash
cc -O2 -Wall -Wextra -Werror -o /tmp/rob_window_probe rob_window_probe.c
```

**Android 目标板交叉编译**（同 TLB 探针工具链，NDK r26+，Rosetta 运行 x86_64 工具链）：

```bash
NDK=~/Library/Android/sdk/ndk/27.0.12077973
CC=$NDK/toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android34-clang
$CC -O2 -Wall -Wextra -Werror -static -o rob_window_probe rob_window_probe.c
```

## 生成机器码人工检查（矩阵 B5 / 报告 §5.1-2，硬门槛）

被测指令序列由手写发射器生成（编译器不可见），每次修改发射器后：

```bash
# 1) 导出生成码（默认参数即可，地址字段会烘焙进去，对比时忽略 mov/movk 的立即数）
./rob_window_probe -t nop -n 64 --write-asm /tmp/rob_nop64.bin
# 2) 反汇编检查：指令数、依赖关系、分支布局
objdump -D -b binary -m aarch64 /tmp/rob_nop64.bin        # Linux/Android
#    macOS 无 -b 支持：用 capstone（pip install capstone）或 llvm-objdump --triple=arm64
# 3)（v2 目标）黄金汇编回归：robsize check-gold.sh 同款，生成码入库逐字节 diff
```

v0.1 冒烟已核验（capstone 反汇编）：常量区 → 着陆区 → 循环体布局正确；`n=64,comp=1` 时总指令数 79（12 常量 + 2 对齐 + 64 着陆 + 1+62+1 锚点填充 + 2 循环控制 + 1 ret 的组成可逐条对上）。

**v0.1 冒烟实测抓出的两个 bug（已修，留档防回归）**：①入口抖动曾落在常量区中段，跳过 `x2` 迭代计数装载 → 用调用方残留值死循环；修复 = 着陆区（64B NOP）置于**常量区之前**（robsize prologue-first 结构），任何抖动偏移都必经常量区。②着陆偏移曾误用指令序号当字节偏移。

## 运行（目标板，需 root）

```bash
adb push rob_window_probe /data/local/tmp/ && adb shell
sailfish:/data/local/tmp # su
# E1 主扫描：N=1..1024，每 N 独立进程（J1 门控要求 walk 足迹 > L2）
for n in $(seq 1 1024); do
  taskset 80 ./rob_window_probe -t nop -n $n --pin 7 \
      -e 0x24 -e 0x816D --rawlog raw_n$n.csv
done
# E2 类别矩阵（示例：ADD 类，预注册补偿 -2）
for n in $(seq 300 500); do
  taskset 80 ./rob_window_probe -t add -n $n --pin 7 --rawlog raw_add_n$n.csv
done
# 锚点 C 档（fsqrt 链，J8 跨锚点判据；须先做 E0-6 标定）
taskset 80 ./rob_window_probe -t nop -n 400 -a fsqrt --pin 7 --rawlog raw_c_n400.csv
# simpleperf 等价：simpleperf stat -e r11,r1b,r8 -- taskset 80 ./rob_window_probe -t nop -n 64
```

**关键参数口径**：
- `-i its`（默认 262144）：J1 门控要求 walk 足迹 ≈ its×8B 超过目标 L2；标定不足时锚点不 miss，拐点整体消失。小 its（如冒烟用的 100）只走热链，**时延数值无意义**。
- `-l n`（默认 1024）：chase 远跳间隔（步）；与 `-i` 共同决定 miss 行为，冻结后不得改。
- 补偿口径：`needs_comp=1` 的类别（除 fadd 外全部）实际发射 N−2 条（两锚点 load 占位），判读时 W 带 ±2 不确定带（报告 §5.8-J7）。
- `-a fsqrt` 模式不分配 chase 缓冲（无存储器参与）；**启用前必须完成 E0-6**（fsqrt 延迟与 µOP 粒度标定）。

**PMU 失败路径**（TLB 评审 2-6 教训内置）：事件打开失败明确打印 n/a 并跳过该事件，绝不输出 0；组读带 TIME_ENABLED/TIME_RUNNING。

## 纪律对照（报告 §5.7）

| 纪律 | 实现状态 |
|---|---|
| 生成码人工检查 / 黄金回归 | ✅ 检查流程本文档化；黄金回归 v2 |
| 瞬态/稳态分分析 | ✅ 逐轮 rawlog（首轮不剔，分析侧按判据处理） |
| 空窗对照 | ⚠️ 未实现 `-n 0` 特殊路径（v2；当前用 `-n 3` 最小块近似） |
| 锁核/THP | ✅ `--pin` 失败即退出；`MADV_NOHUGEPAGE` |
| 失败数据落盘 | ⚠️ 探针只打印 n/a；结构化 failure 记录归外层脚本（v2） |
| 单变量控制 | ✅ 类别间仅发射器函数不同 |
