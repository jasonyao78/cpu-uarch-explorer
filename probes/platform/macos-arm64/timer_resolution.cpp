// SPDX-License-Identifier: Apache-2.0
// timer_resolution: 测量 macOS 计时原语 mach_absolute_time 的
// 分辨率与单次调用开销（macos-arm64 平台能力探针，结果登记于需求 v0.3 §2.1，
// runner/targets 的 capability discovery 将复用本探针的结论）。
//
// 技术原理
// --------
// 1. mach_absolute_time 是什么
//    macOS 用户态能拿到的最底层计时原语：返回系统启动以来的"时钟滴答"数，
//    单位**不是纳秒**。换算必须由 mach_timebase_info 给出的比例完成：
//        纳秒 = ticks × numer / denom
//    本机实测 numer/denom = 125/3，即 1 tick = 41.6667 ns（24 MHz 计数器）。
//    clock_gettime(CLOCK_MONOTONIC) 底层是同一个计数器，只是返回值已换算成
//    秒/纳秒，两者等价。
//
// 2. 如何测"分辨率"（有效粒度）
//    连续背靠背读计时器两次，差值只可能是 0 或 k×粒度。粒度为 G 时，大量
//    相邻读数会落进同一 tick（零间隔），所有非零差值中的最小值 ≈ G。
//    因此统计 100 万次相邻差值：
//      - zero_delta 比例 —— 调用速率与 tick 速率之比的直观度量，比例越高
//        说明粒度相对调用越粗；
//      - 非零最小差值 —— 有效分辨率，这是微基准能分辨的最小时间间隔。
//
// 3. 如何测"调用开销"
//    循环 N 次调用并整体计时，摊薄得到单次开销；跑多轮取最小值，因为
//    中断/调度噪声只会拖慢不会加速，最小值最接近真实开销。
//    开销与分辨率共同决定"多短的区间值得计时"：L1 级 load 延迟 ~1 ns，
//    远低于 41.67 ns 粒度，所以单次计时区间必须装下 ≥10^5 次 load，
//    让量化噪声在平均中相互抵消（本仓所有微基准的 -n 默认值都据此设定）。
//
// 输出：key=value 行到 stdout，供 runner 层包装为 record.schema.json 记录。

#include <cstdio>
#include <cstdint>
#include <mach/mach_time.h>

int main() {
    // 1. 读 timebase 比例，得到 tick → 纳秒的换算系数
    mach_timebase_info_data_t tb;
    mach_timebase_info(&tb);
    const double ns_per_tick = static_cast<double>(tb.numer) / tb.denom;
    std::printf("timebase numer=%u denom=%u (1 tick = %.6f ns)\n",
                tb.numer, tb.denom, ns_per_tick);

    // 2. 分辨率：统计相邻两次读数的差值分布
    const int SAMPLES = 1000000;
    uint64_t prev = mach_absolute_time();
    uint64_t min_delta = ~0ULL, max_delta = 0;
    long long zero_deltas = 0;
    for (int i = 0; i < SAMPLES; ++i) {
        const uint64_t t = mach_absolute_time();
        const uint64_t d = t - prev;
        if (d == 0) {
            ++zero_deltas;          // 两次读数落进同一 tick：粒度比调用间隔粗
        } else {
            if (d < min_delta) min_delta = d;   // 非零最小差 ≈ 计数器粒度
            if (d > max_delta) max_delta = d;   // 最大值仅反映调度噪声，无物理意义
        }
        prev = t;
    }
    std::printf("samples=%d zero_delta=%lld (%.1f%%) min_delta=%llu ticks (%.2f ns) max_delta=%llu ticks\n",
                SAMPLES, zero_deltas, 100.0 * zero_deltas / SAMPLES,
                min_delta, min_delta * ns_per_tick, max_delta);

    // 3. 开销：摊薄测量 + 多轮取最小值
    const int ROUNDS = 5, CALLS = 10000000;
    double best = 1e30;
    for (int r = 0; r < ROUNDS; ++r) {
        const uint64_t t0 = mach_absolute_time();
        uint64_t acc = 0;
        for (int i = 0; i < CALLS; ++i) acc += mach_absolute_time();
        const uint64_t t1 = mach_absolute_time();
        const double per = (t1 - t0) * ns_per_tick / CALLS;
        if (per < best) best = per;
        if (acc == 42) std::printf("unreachable\n"); // sink：acc 必须被消费，累加才不会被优化掉
    }
    std::printf("call_overhead_best_ns=%.2f (%d calls x %d rounds)\n", best, CALLS, ROUNDS);
    return 0;
}
