// tlb_capacity_probe.c — §5.3/§5.4 改进版指针追逐容量扫描探针（v2，外部评审修订）
//
// 对应报告：《TLB微架构深度分析报告》§5.3（容量扫描）、§5.4（L1 全相联验证）、
// §3.3/M4（in-flight 翻译并行度）。
// 设计要点（相对 lmbench tlb.c 的修正）：
//   1. 预热与测量显式分离；
//   2. PMU 事件同步采集（perf_event_open，Linux）；
//   3. 细粒度扫描由外层脚本驱动本程序逐点执行（每配置独立进程 = 独立重复）；
//   4. 四种页分布（v2 修正 R4）：
//      -d 0 连续页号集合 {0..N-1}
//      -d 1 大步距集合 {i×stride}（按 N×stride 分配区域，v1 的越界 bug 已修）
//      -d 2 随机**集合**：从大区域随机取 N 个不同页号（真分布对照）
//      -d 3 随机**顺序**：lmbench 式 {0..N-1} 的排列（只改访问顺序，保留对照）
//   5. 全部访问地址落盘（--addrlog）；
//   6. M4（v2 重构，回应评审 R2）：**单条串行依赖链任意时刻只有 1 个 outstanding
//      翻译 miss，测不了并行 walk 深度**。新增 -K 独立链模式：区域切成 K 份、每份
//      一条独立链，宏轮内逐拍交错推进（for step { for k { p[k] = *p[k]; } }），
//      K 路互不依赖的翻译 miss 可同时在飞；配合 0x8128 DTLB_WALK_PERCYC
//      （每周期在飞 walk 数）找饱和点。-m fast|slow 保留为辅助观察（频率/排队
//      效应），不再声称测并行度。
//
// 地面真值（X4 TRM Table 5-1）：L1 dTLB = 96 条全相联；L2 TLB = 2048 条 8-way。
// 判据：L1D_TLB_REFILL 首个抬升平台 N≈96；L2D_TLB_REFILL 抬升点 N≈2048。
// 并行 walk 判据：每链工作集需 > 2048 页（保证 L2 miss→walk）；K 递增时
//   DTLB_WALK_PERCYC 均值上升至饱和平台，平台值 ≈ 并行 walk 深度。
//
// 编译：gcc -O2 -Wall -Wextra -Werror -o tlb_capacity_probe tlb_capacity_probe.c
// 用法：
//   ./tlb_capacity_probe -N 96  -R 200 -d 2 -e 0x0005 -e 0x002D --addrlog a.txt
//   ./tlb_capacity_probe -N 4096 -R 20 -K 8 -e 0x8128        # M4：8 独立链并行度
//   ./tlb_capacity_probe -N 96  -R 200 -d 1 -s 256           # 大步距集合
// Android（SM8650）：simpleperf stat -e r5,r2d -- taskset 80 ./tlb_capacity_probe ...
//
// 注意：本骨架是"可编译、可跑通流程"的基础版；正式实验需补：错误处理完善、
//       置信区间统计（建议外壳脚本做）、DVFS 记录、IRQ 屏蔽。

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/mman.h>
#ifdef __linux__
#include <sched.h>
#include <sys/syscall.h>
#include <linux/perf_event.h>
#endif

static long g_pagesz;
static volatile char *g_sink;

// ---------- 工具 ----------

static double now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec * 1e9 + (double)ts.tv_nsec;
}

static double percentile_ns(double *sorted, int n, double q) {
    if (n <= 0) return 0.0;
    int idx = (int)(q * (n - 1) + 0.5);
    if (idx < 0) idx = 0;
    if (idx > n - 1) idx = n - 1;
    return sorted[idx];
}

static int dbl_cmp(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return x < y ? -1 : x > y;
}

// ---------- 页分布（v2：真集合） ----------
// 输入 n = 访问页数；输出 order[n]（页号）与所需区域页数 region_pages。
//   mode 0: 连续集合 {0..n-1}
//   mode 1: 大步距集合 {i*stride}（区域 n*stride）
//   mode 2: 随机集合：从 [0, region) 随机取 n 个不同页号（区域 ≥ 16n）
//   mode 3: 随机顺序：{0..n-1} 的排列（lmbench 式，只改访问顺序）
static void gen_page_set(size_t *order, int n, int mode, size_t stride,
                         size_t *region_pages) {
    if (mode == 1) {
        *region_pages = (size_t)n * stride;
        for (int i = 0; i < n; i++) order[i] = (size_t)i * stride;
        return;
    }
    if (mode == 2) {
        *region_pages = (size_t)n * 16;
        if (*region_pages < 4096) *region_pages = 4096;
        // 随机集合：Fisher-Yates 取前 n 个
        size_t m = *region_pages;
        size_t *all = malloc(sizeof(size_t) * m);
        for (size_t i = 0; i < m; i++) all[i] = i;
        srand(12345);
        for (int i = 0; i < n; i++) {
            int j = i + rand() % (int)(m - i);
            size_t t = all[i]; all[i] = all[j]; all[j] = t;
            order[i] = all[i];
        }
        free(all);
        return;
    }
    *region_pages = (size_t)n;
    for (int i = 0; i < n; i++) order[i] = (size_t)i;
    if (mode == 3) {
        srand(12345);
        for (int i = n - 1; i > 0; i--) {
            int j = rand() % (i + 1);
            size_t t = order[i]; order[i] = order[j]; order[j] = t;
        }
    }
}

// ---------- PMU ----------

#ifdef __linux__
static int perf_open(uint32_t event_no, int cpu) {
    struct perf_event_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.size = sizeof(attr);
    attr.type = PERF_TYPE_RAW;
    attr.config = event_no;
    attr.exclude_kernel = 0;
    attr.exclude_hv = 0;
    return (int)syscall(SYS_perf_event_open, &attr, 0, -1, -1, 0);
}
static uint64_t perf_read(int fd) {
    uint64_t v = 0;
    if (fd >= 0 && read(fd, &v, sizeof(v)) != sizeof(v)) return UINT64_MAX;
    return v;
}
#else
static int perf_open(uint32_t e, int c) { (void)e; (void)c; return -1; }
static uint64_t perf_read(int fd) { (void)fd; return UINT64_MAX; }
#endif

// ---------- 主流程 ----------

int main(int argc, char **argv) {
    int n_pages = 96, reps = 20, mode = 2, pin_cpu = -1;
    int n_chains = 1;                   // M4 v2：独立链数 K
    int slow = 0;
    long round_delay_ns = 20000;
    size_t stride = 256;
    uint32_t events[4]; int n_events = 0;
    const char *addrlog = NULL;

    for (int i = 1; i < argc; i++) {
        if      (!strcmp(argv[i], "-N") && i+1 < argc) n_pages  = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-R") && i+1 < argc) reps     = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-d") && i+1 < argc) mode     = atoi(argv[++i]); // 0/1/2/3
        else if (!strcmp(argv[i], "-K") && i+1 < argc) n_chains = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-s") && i+1 < argc) stride   = strtoul(argv[++i], 0, 0);
        else if (!strcmp(argv[i], "-e") && i+1 < argc && n_events < 4)
            events[n_events++] = (uint32_t)strtoul(argv[++i], 0, 0);
        else if (!strcmp(argv[i], "--pin") && i+1 < argc) pin_cpu = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--addrlog") && i+1 < argc) addrlog = argv[++i];
        else if (!strcmp(argv[i], "-m") && i+1 < argc) {
            const char *mv = argv[++i];
            if      (!strcmp(mv, "slow")) slow = 1;
            else if (!strcmp(mv, "fast")) slow = 0;
            else { fprintf(stderr, "-m fast|slow\n"); return 2; }
        }
        else if (!strcmp(argv[i], "--round-delay-ns") && i+1 < argc)
            round_delay_ns = strtol(argv[++i], 0, 0);
        else { fprintf(stderr, "usage: %s -N pages -R reps -d 0|1|2|3 [-s stride] "
            "[-K chains] [-e event]* [--pin cpu] [--addrlog f] [-m fast|slow] "
            "[--round-delay-ns ns]\n", argv[0]); return 2; }
    }
    if (reps < 3) { fprintf(stderr, "-R >= 3 required for percentiles\n"); return 2; }
    if (mode < 0 || mode > 3) { fprintf(stderr, "-d 0..3\n"); return 2; }

    g_pagesz = sysconf(_SC_PAGESIZE);

#ifdef __linux__
    if (pin_cpu >= 0) {
        cpu_set_t set; CPU_ZERO(&set); CPU_SET(pin_cpu, &set);
        if (sched_setaffinity(0, sizeof(set), &set)) perror("sched_setaffinity");
    }
#endif

    // K 条独立链：区域切成 K 份，每份 n_pages 页、各自建链（每链工作集独立，
    // 用于并行 walk 探测时每链需 > 2048 页以持续产生 L2 miss → walk）。
    size_t region_pages;
    size_t *order = malloc(sizeof(size_t) * n_pages);
    gen_page_set(order, n_pages, mode, stride, &region_pages);

    size_t total = (size_t)n_chains * region_pages * (size_t)g_pagesz;
    char *base = mmap(NULL, total, PROT_READ | PROT_WRITE,
                      MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (base == MAP_FAILED) { perror("mmap"); return 1; }

    // 建链：链 k 的页 k*region_pages + order[i]，页首字指向链内下一页（环形）
    char **heads = malloc(sizeof(char *) * n_chains);
    for (int k = 0; k < n_chains; k++) {
        char *sub = base + (size_t)k * region_pages * (size_t)g_pagesz;
        for (int i = 0; i < n_pages; i++) {
            char *cur  = sub + order[i] * (size_t)g_pagesz;
            char *next = sub + order[(i + 1) % n_pages] * (size_t)g_pagesz;
            *(char **)cur = next;
        }
        heads[k] = sub + order[0] * (size_t)g_pagesz;
    }

    // 地址落盘（最终虚拟地址）
    if (addrlog) {
        FILE *f = fopen(addrlog, "w");
        for (int k = 0; k < n_chains; k++)
            for (int i = 0; i < n_pages; i++)
                fprintf(f, "%p\n", (void *)(base + ((size_t)k * region_pages + order[i])
                                                   * (size_t)g_pagesz));
        fclose(f);
    }

    // 预热：每链整链一轮
    for (int k = 0; k < n_chains; k++) {
        char *p = heads[k];
        for (int i = 0; i < n_pages; i++) p = *(char **)p;
    }

    int fds[4];
    for (int i = 0; i < n_events; i++) fds[i] = perf_open(events[i], pin_cpu);
#ifdef __linux__
    for (int i = 0; i < n_events; i++) ioctl(fds[i], PERF_EVENT_IOC_RESET, 0);
    for (int i = 0; i < n_events; i++) ioctl(fds[i], PERF_EVENT_IOC_ENABLE, 0);
#endif

    // 测量：reps 个宏轮；宏轮内逐拍交错推进 K 条链（K 路独立翻译 miss 可并行）。
    // 编译屏障防重排消除（开发实测 clang -O2 会删未用结果的追逐循环）。
    char **ps = malloc(sizeof(char *) * n_chains);
    memcpy(ps, heads, sizeof(char *) * n_chains);
    double *round_ns = malloc(sizeof(double) * reps);
    asm volatile("" ::: "memory");
    double t0 = now_ns();
    for (long r = 0; r < reps; r++) {
        double rs = now_ns();
        for (int i = 0; i < n_pages; i++)
            for (int k = 0; k < n_chains; k++)
                ps[k] = *(char *volatile *)ps[k];
        round_ns[r] = now_ns() - rs;
        if (slow) {
            double deadline = rs + (double)round_delay_ns;
            while (now_ns() < deadline) { /* busy-wait */ }
        }
    }
    double t1 = now_ns();
    asm volatile("" ::: "memory");
    g_sink = ps[0];

#ifdef __linux__
    for (int i = 0; i < n_events; i++) ioctl(fds[i], PERF_EVENT_IOC_DISABLE, 0);
#endif

    double *sorted = malloc(sizeof(double) * reps);
    memcpy(sorted, round_ns, sizeof(double) * reps);
    qsort(sorted, reps, sizeof(double), dbl_cmp);
    double p50 = percentile_ns(sorted, reps, 0.50);
    double p90 = percentile_ns(sorted, reps, 0.90);
    double p99 = percentile_ns(sorted, reps, 0.99);
    double rmax = sorted[reps - 1];

    long loads = (long)reps * n_pages * n_chains;
    printf("N=%d mode=%d K=%d m=%s loads=%ld ns_per_load=%.3f "
           "p50=%.0f p90=%.0f p99=%.0f max=%.0f ns/round",
           n_pages, mode, n_chains, slow ? "slow" : "fast", loads,
           (t1 - t0) / loads, p50, p90, p99, rmax);
    for (int i = 0; i < n_events; i++) {
        uint64_t v = perf_read(fds[i]);
        if (v == UINT64_MAX) printf(" event0x%x=n/a(non-Linux/no-perm)", events[i]);
        else                 printf(" event0x%x=%llu", events[i], (unsigned long long)v);
    }
    printf("\n");

    free(ps); free(round_ns); free(sorted); free(heads); free(order);
    munmap(base, total);
    return 0;
}
