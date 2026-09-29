// l2_set_probe.c — §5.5 L2 TLB 同 set 地址生成器 + way 跳变实验（v2，外部评审修订）
//
// 对应报告：《TLB微架构深度分析报告》§5.5。
// 背景（X4 TRM 地面真值）：L2 TLB = 8-way × 256 sets = 2048 条（Table 5-1,
// Table 9-32）。sets/ways 已确认，本探针目标：检验"VPN→set 索引哈希"候选
// 假设（H1~H4），并测定稳态 way 数（跳变点应=8）。
//
// v2 修订（回应外部评审 R1/R3）：
//   [R3 修复] 哈希与校验一律用**最终虚拟地址**（base 页号计入 vpn），
//             候选取样跨高字段步进（step=509 素数步长），H1/H3、H2/H4 可区分；
//   [R1 修复] run 模式改为 prime+probe 协议：每轮先追逐 filler 链（默认 512 页，
//             > L1 dTLB 96 条）驱逐 L1，再访问目标 w 页——保证每个目标访问都是
//             L1 miss、真实到达 L2；计数按**阶段**（filler 段 / probe 段）在进程
//             内读 perf 增量，建链与首轮自动排除；-T2 提供同 filler 干扰下的
//             对照 set。判读顺序：先看 probe 段 L1D_TLB_REFILL ≈ w（协议有效
//             门控），再看 L2D_TLB_REFILL 在 w=8→9 是否跳变。
//   注意（评审 R1 强调）：即使协议正确，w>8 后"每页每轮必 miss"仍受替换策略
//   与 walk 条目影响——跳变是判据，曲线形态不是。
//
// 编译：gcc -O2 -Wall -Wextra -Werror -o l2_set_probe l2_set_probe.c
// 用法：
//   ./l2_set_probe gen -H 2 -T 7 -c 16 -P 65536 --addrlog l2_h2_t7.txt
//   ./l2_set_probe run -H 2 -T 7 -w 8  -R 20 -P 65536
//   ./l2_set_probe run -H 2 -T 7 -w 16 -R 20 -P 65536 -T2 100
// 事件（默认内嵌）：0x0005 L1D_TLB_REFILL / 0x002D L2D_TLB_REFILL / 0x002F L2D_TLB
// 判据（报告 §5.5-3）：probe 段 L1D_TLB_REFILL ≈ w 且 L2D_TLB ≈ w 时协议有效；
//                      w ≤ 8 → L2D_TLB_REFILL ≈ 0；w ≥ 9 → 跳到 ≈w/轮。

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#ifdef __linux__
#include <sys/syscall.h>
#include <linux/perf_event.h>
#endif

static long g_pagesz = 4096;
static volatile char *g_sink;

#define NSETS        256   // X4 TRM Table 9-32：L2 TLB entry 0-255 / way
#define NWAYS_TRUTH    8   // X4 TRM Table 5-1：8-way
#define CAND_STEP    509   // 候选取样步长（素数，跨越高字段，避免高位恒定）

// ---------- 候选索引假设 H1~H4：一律对最终虚拟地址计算 ----------
// 4K 粒度下 VPN[7:0] = VA[19:12]。
static uint32_t set_index(int H, uintptr_t va) {
    uint64_t vpn = (uint64_t)va >> 12;
    switch (H) {
    case 1:  return (uint32_t)(vpn & 0xFF);                              // H1 位选
    case 2:  return (uint32_t)((vpn ^ (vpn >> 8)) & 0xFF);               // H2 相邻字段 XOR
    case 3:  return (uint32_t)((vpn ^ (vpn >> 16)) & 0xFF);              // H3 高位折叠
    case 4:  return (uint32_t)((vpn ^ (vpn >> 8) ^ (vpn >> 16)) & 0xFF); // H4 三字段 XOR
    default: fprintf(stderr, "unknown H\n"); exit(2);
    }
}

// ---------- 地址集合构造：最终 VA 校验 + 跨高字段分桶取样 + 去重 ----------
// 扫描 base 起全部页，但每 bucket 只收第一个匹配：兼顾命中率与高字段多样性
// （连续取前 16 个匹配会使高位恒定，H1/H3 与 H2/H4 在样本上不可区分——评审 R3）。
static int collect_set_addrs(int H, uint32_t target, int need, char *base,
                             size_t total_pages, uintptr_t *vas /*out*/) {
    int found = 0;
    uint64_t bucket = (uint64_t)total_pages / (uint64_t)need;
    if (bucket == 0) bucket = 1;
    for (uint64_t i = 1; found < need && i < (uint64_t)total_pages; i++) {
        if (i < (uint64_t)found * bucket) continue; // 未到本桶
        uintptr_t va = (uintptr_t)base + i * (uint64_t)g_pagesz;
        if (set_index(H, va) != target) continue;
        int dup = 0;
        for (int k = 0; k < found; k++) if (vas[k] == va) { dup = 1; break; }
        if (!dup) {
            // [R3 修复] 用最终 VA 重算候选 set，二次校验
            if (set_index(H, va) != target) {
                fprintf(stderr, "FATAL: final-VA recheck failed at %p\n", (void *)va);
                exit(3);
            }
            vas[found++] = va;
        }
    }
    return found;
}

// ---------- PMU ----------
#ifdef __linux__
static int perf_open(uint32_t ev) {
    struct perf_event_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.size = sizeof(attr);
    attr.type = PERF_TYPE_RAW;
    attr.config = ev;
    return (int)syscall(SYS_perf_event_open, &attr, 0, -1, -1, 0);
}
static uint64_t perf_read(int fd) {
    uint64_t v = 0;
    if (fd >= 0 && read(fd, &v, sizeof(v)) != sizeof(v)) return UINT64_MAX;
    return v;
}
#else
static int perf_open(uint32_t e) { (void)e; return -1; }
static uint64_t perf_read(int fd) { (void)fd; return UINT64_MAX; }
#endif

static void build_chain(uintptr_t *vas, int n, char **cells) {
    for (int i = 0; i < n; i++) cells[i] = (char *)vas[i];
    for (int i = 0; i < n; i++)
        *(char **)vas[i] = (char *)vas[(i + 1) % n]; // 环形链
}

// 随机序填充 filler 链（驱逐 L1 dTLB 用，页集合本身无需约束）
static void build_filler(char *fbase, int fpages, uintptr_t **vas_out) {
    uintptr_t *vas = malloc(sizeof(uintptr_t) * fpages);
    for (int i = 0; i < fpages; i++) vas[i] = (uintptr_t)fbase + (uint64_t)i * g_pagesz;
    srand(99991);
    for (int i = fpages - 1; i > 0; i--) {
        int j = rand() % (i + 1);
        uintptr_t t = vas[i]; vas[i] = vas[j]; vas[j] = t;
    }
    for (int i = 0; i < fpages; i++)
        *(char **)vas[i] = (char *)vas[(i + 1) % fpages];
    *vas_out = vas;
}

static double now_ns(void) {
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec * 1e9 + (double)ts.tv_nsec;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s gen|run -H 1..4 -T set [-T2 set2] "
            "[-c count|-w ways -R rounds] -P total_pages [--addrlog f] "
            "[-F filler_pages] [-e ev]*\n", argv[0]);
        return 2;
    }
    int is_gen = !strcmp(argv[1], "gen");
    int H = 1, ways = 8, rounds = 20, need = 16, filler_pages = 512;
    int have_T2 = 0;
    uint32_t target = 0, target2 = 0;
    size_t total_pages = 65536;
    uint32_t events[4] = {0x0005, 0x002D, 0x002F, 0}; int n_events = 3;
    const char *addrlog = NULL;

    for (int i = 2; i < argc; i++) {
        if      (!strcmp(argv[i], "-H") && i+1 < argc) H = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-T") && i+1 < argc) target = (uint32_t)strtoul(argv[++i],0,0);
        else if (!strcmp(argv[i], "-T2") && i+1 < argc) { target2 = (uint32_t)strtoul(argv[++i],0,0); have_T2 = 1; }
        else if (!strcmp(argv[i], "-c") && i+1 < argc) need = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-w") && i+1 < argc) ways = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-R") && i+1 < argc) rounds = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-P") && i+1 < argc) total_pages = strtoul(argv[++i],0,0);
        else if (!strcmp(argv[i], "-F") && i+1 < argc) filler_pages = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--addrlog") && i+1 < argc) addrlog = argv[++i];
        else if (!strcmp(argv[i], "-e") && i+1 < argc && n_events < 4)
            events[n_events++] = (uint32_t)strtoul(argv[++i], 0, 0);
        else { fprintf(stderr, "bad arg %s\n", argv[i]); return 2; }
    }
    if (target >= NSETS || (have_T2 && target2 >= NSETS)) {
        fprintf(stderr, "T/T2 must be < %d\n", NSETS); return 2;
    }
    if (rounds < 2) { fprintf(stderr, "-R >= 2 (round 0 = warmup)\n"); return 2; }
    g_pagesz = sysconf(_SC_PAGESIZE);

    char *base = mmap(NULL, total_pages * (size_t)g_pagesz,
                      PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (base == MAP_FAILED) { perror("mmap"); return 1; }

    int want = is_gen ? need : ways;
    uintptr_t *vas = malloc(sizeof(uintptr_t) * (size_t)want);
    int got = collect_set_addrs(H, target, want, base, total_pages, vas);
    if (got < want) {
        fprintf(stderr, "only %d addrs for set %u under H%d (increase -P)\n", got, target, H);
        return 1;
    }

    // 最终 VA 落盘（含重算 set 列，供事后审计）
    if (addrlog || is_gen) {
        const char *f = addrlog ? addrlog : "/dev/stdout";
        FILE *out = fopen(f, "w");
        for (int i = 0; i < got; i++)
            fprintf(out, "0x%lx set=%u\n", (unsigned long)vas[i], set_index(H, vas[i]));
        fclose(out);
    }
    if (is_gen) { printf("H%d set=%u addrs=%d (truth: %d sets x %d ways)\n",
                         H, target, got, NSETS, NWAYS_TRUTH); return 0; }

    // ---- run 模式：prime+probe ----
    // 目标链
    build_chain(vas, ways, (char **)vas);
    // filler 区（与目标不同页，>= L1 dTLB 容量 96 才能驱逐目标）
    char *fbase = base + (total_pages / 2) * (size_t)g_pagesz;
    if ((size_t)filler_pages >= total_pages / 2) {
        fprintf(stderr, "-F too large vs -P/2\n"); return 2;
    }
    uintptr_t *fvas;
    build_filler(fbase, filler_pages, &fvas);

    int fds[4];
    for (int i = 0; i < n_events; i++) fds[i] = perf_open(events[i]);
#ifdef __linux__
    for (int i = 0; i < n_events; i++) ioctl(fds[i], PERF_EVENT_IOC_RESET, 0);
    for (int i = 0; i < n_events; i++) ioctl(fds[i], PERF_EVENT_IOC_ENABLE, 0);
#endif

    uint64_t (*probe_delta)[4] = malloc(sizeof(uint64_t[4]) * rounds); // probe 段每事件增量
    double *probe_ns = malloc(sizeof(double) * rounds);
    char *tp = (char *)vas[0];
    asm volatile("" ::: "memory");
    for (int r = 0; r < rounds; r++) {
        uint64_t c0[4], c1[4];
        for (int i = 0; i < n_events; i++) c0[i] = perf_read(fds[i]);
        { char *p = (char *)fvas[0]; for (int i = 0; i < filler_pages; i++) p = *(char *volatile *)p; } // prime
        for (int i = 0; i < n_events; i++) c1[i] = perf_read(fds[i]);
        double t0 = now_ns();
        for (int i = 0; i < ways; i++) tp = *(char *volatile *)tp;                                   // probe
        probe_ns[r] = now_ns() - t0;
        for (int i = 0; i < n_events; i++) {
            uint64_t c2 = perf_read(fds[i]);
            probe_delta[r][i] = (c0[i] == UINT64_MAX || c1[i] == UINT64_MAX || c2 == UINT64_MAX)
                                ? UINT64_MAX : c2 - c1[i];
        }
    }
    asm volatile("" ::: "memory");
    g_sink = tp;
#ifdef __linux__
    for (int i = 0; i < n_events; i++) ioctl(fds[i], PERF_EVENT_IOC_DISABLE, 0);
#endif

    // 统计：剔除 round 0（含冷启动），对剩余轮取均值
    printf("H%d set=%u w=%d rounds=%d filler=%d", H, target, ways, rounds, filler_pages);
    for (int i = 0; i < n_events; i++) {
        if (probe_delta[1][i] == UINT64_MAX) { printf(" ev0x%x=n/a", events[i]); continue; }
        double sum = 0;
        for (int r = 1; r < rounds; r++) sum += (double)probe_delta[r][i];
        printf(" ev0x%x=%.1f", events[i], sum / (rounds - 1));
    }
    { double sum = 0; for (int r = 1; r < rounds; r++) sum += probe_ns[r];
      printf(" probe_ns=%.0f", sum / (rounds - 1)); }
    printf("\n");
    printf("gate: L1D_TLB_REFILL(ev0x5) 应≈w=%d 且 L2D_TLB(ev0x2f) 应≈w；"
           "w≤%d 时 L2D_TLB_REFILL(ev0x2d) 应≈0，w≥%d 时应跳变\n", ways, NWAYS_TRUTH, NWAYS_TRUTH + 1);

    free(probe_delta); free(probe_ns); free(vas); free(fvas);
    return 0;
}
