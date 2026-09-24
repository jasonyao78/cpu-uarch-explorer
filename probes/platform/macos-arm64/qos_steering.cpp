// SPDX-License-Identifier: Apache-2.0
// qos_steering: 验证 Apple Silicon 上 QoS → P/E cluster 分流的可靠性
// （macos-arm64 平台能力探针，结果登记于需求 v0.3 §2.1）。
//
// 技术原理
// --------
// 1. 为什么要这个探针
//    Apple Silicon 没有 Linux 式的 sched_setaffinity 精确绑核，用户态
//    唯一能影响"线程落在 P 核还是 E 核"的手段是 QoS 服务类
//    （pthread_set_qos_class_self_np）。经验规则是：
//    USER_INTERACTIVE / DEFAULT → Performance cluster；
//    BACKGROUND                → Efficiency cluster。
//    但规则是否可靠、换 QoS 后是否可复现，必须用实验证实——本探针就是
//    这个证实。它是 macOS 后端 E-core 测量手段（"BACKGROUND 即绑 E 核"）
//    的依据。
//
// 2. 如何"看见"自己落在哪种核上
//    用户态没有任何 API 直接报告当前核心类型，只能用间接判据：同代
//    Apple Silicon 的 P 核与 E 核在依赖链延迟上差距巨大（本机实测吞吐
//    差 3.8×）。因此跑一个延迟受限（latency-bound）的固定工作负载，
//    吞吐呈双峰分布即证明分流生效；单峰或漂移则说明规则失效。
//
// 3. 为什么工作负载选 LCG 串行链（x = x*A + C）
//    - 每一步乘加都依赖上一步的结果，硬件无法跨迭代并行，吞吐 =
//      1/依赖链延迟 → 对核心类型最敏感；
//    - 全程操作在寄存器内，不碰内存 → 不受缓存/访存状态干扰；
//    - volatile 阻止编译器把循环优化成闭合形式（闭式解会把测量变成
//      一次 O(1) 计算，吞吐失真）。
//    使用 Knuth/MMIX 推荐的常数对，乘法溢出按 2^64 模回绕不影响链的
//    串行性。
//
// 4. 测量口径
//    每种 QoS 跑 3 轮取最小值：调度抖动与 DVFS 只会拖慢不会加速，
//    最小值最接近稳态。最后把 INTERACTIVE 再测一次，验证"从 E 核
//    回来之后仍能回到 P 核"（分流的可复现性）。
//
// 已知偏差：x 是 volatile，每次迭代的写都要经 store-to-load forwarding
// 才能被下一次乘法读到，绝对值因此含 ~5 周期/迭代的测量开销；本探针
// 证明的是分流的**双峰性**，不是 P/E 核的精确 IPC 比。

#include <cstdio>
#include <cstdint>
#include <pthread.h>
#include <sys/qos.h>
#include <mach/mach_time.h>

static double now_ns() {
    static double ns_per_tick = 0;
    if (ns_per_tick == 0) {
        mach_timebase_info_data_t tb;
        mach_timebase_info(&tb);
        ns_per_tick = static_cast<double>(tb.numer) / tb.denom;
    }
    const uint64_t t = mach_absolute_time();
    return t * ns_per_tick;
}

static double run_once(long long iters) {
    volatile uint64_t x = 0x1234567887654321ULL;
    const double t0 = now_ns();
    for (long long i = 0; i < iters; ++i)
        x = x * 6364136223846793005ULL + 1442695040888963407ULL;
    const double t1 = now_ns();
    if (x == 1) std::printf("unreachable\n"); // sink：消费 x，链不可被消除
    return (t1 - t0) / iters;
}

static void probe(const char* name, qos_class_t q) {
    // set_rc=0 仅说明 QoS 设置成功；是否真的换了核，看吞吐是否跳变
    const int rc = pthread_set_qos_class_self_np(q, 0);
    double best = 1e30;
    for (int r = 0; r < 3; ++r) {
        const double v = run_once(200000000);
        if (v < best) best = v;
    }
    std::printf("qos=%-22s set_rc=%d ns_per_iter_best=%.4f\n", name, rc, best);
}

int main() {
    std::printf("# qos steering probe (bimodal => steering works; ratio ~2+ => P:E)\n");
    probe("USER_INTERACTIVE", QOS_CLASS_USER_INTERACTIVE);
    probe("DEFAULT", QOS_CLASS_DEFAULT);
    probe("BACKGROUND", QOS_CLASS_BACKGROUND);
    probe("USER_INTERACTIVE(2nd)", QOS_CLASS_USER_INTERACTIVE);
    return 0;
}
