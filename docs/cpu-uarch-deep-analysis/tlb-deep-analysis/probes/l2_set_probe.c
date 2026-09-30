// l2_set_probe.c — §5.5 L2 TLB 同 set 地址生成器 + way 跳变实验
//
// 版本记录：
//   v1.0 (2026-09-29) 初版：候选 XOR 反解 + 循环重访 way 测定
//   v2.0 (2026-09-29) 外部评审1（R1/R3）修订：哈希/校验统一最终虚拟地址
//                     （v1 误对相对页号）、候选分桶取样（跨高字段，避免 H1/H3
//                     与 H2/H4 在样本上不可区分）；run 模式改 prime+probe
//                     （filler 驱逐 L1 + 分阶段 PMU 增量 + round 0 剔除 + -T2
//                     对照组）——v1 重访 w≤16 页全驻留 L1，测不到 L2
//   v2.1 (2026-09-29) 外部评审2（源码评审，基于 v1 代码）修订：
//                     - perf 打开失败不再伪报"0 refill"（fd<0 → n/a + 打开时
//                       逐事件告警）；读 time_enabled/time_running，多路复用
//                       时输出 mux 比例提示
//                     - sink 语义修正：char *volatile
//                     - run 模式同样落盘实际使用的目标 VA（v2.0 仅 gen 落盘，
//                       而 gen/run 是不同进程、ASLR 基址不同，审计对不上）
//   v2.2 (2026-09-29) 外部评审3（基于 v2.1，条件性通过）修订：
//                     - [P0-1] filler 改独立 mmap 并与目标/T2 显式断言无交集
//                       （v2.1  filler 固定占映射中间 512 页，目标页可能落入
//                       并被建链覆盖）
//                     - [P0-2] filler 按候选 H 过滤目标 set 的页（v2.1 连续
//                       512 页在 H1 下每 set 恰占 2 页，目标 set 竞争从 w+2
//                       起算）；“w=8→9 干净跳变”在报告中降级为理想预期
//                     - [P0-3] 实现 -T2 真实对照组（每轮 prime 后交替测 T 与
//                       T2 两组，分别输出分阶段计数；v2.1 只解析未运行）
//                     - [P0-4] perf_snap 失败路径不再读未初始化值（s 数组
//                       零初始化）；计数窗口覆盖逐轮快照与 read/计时调用的
//                       固有污染以"每次访问 refill 率"报告对冲
//                     - [P0-5] 页大小 != 4K 直接拒绝（set_index 固定 4K 粒度）；
//                       mmap 后尽力 MADV_NOHUGEPAGE（pagemap 查不了 PTE_CONT，
//                       THP 是唯一可从用户态控制的合组来源）
//
// 对应报告：《TLB微架构深度分析报告》§5.5。
// 背景（X4 TRM 地面真值）：L2 TLB = 8-way × 256 sets = 2048 条（Table 5-1,
// Table 9-32）。sets/ways 已确认，本探针目标：检验"VPN→set 索引哈希"候选
// 假设（H1~H4），并测定稳态 way 数（跳变点应=8）。
//
// 判读顺序：先看 probe 段 L1D_TLB_REFILL ≈ w（协议有效门控），再看
// L2D_TLB_REFILL 在 w=8→9 是否跳变。注意（评审 R1 强调）：即使协议正确，
// w>8 后"每页每轮必 miss"仍受替换策略与 walk 条目影响——跳变是判据，曲线
// 形态不是。
//
// 编译：gcc -O2 -Wall -Wextra -Werror -o l2_set_probe l2_set_probe.c
// 用法：
//   ./l2_set_probe gen -H 2 -T 7 -c 16 -P 65536 --addrlog l2_h2_t7.txt
//   ./l2_set_probe run -H 2 -T 7 -w 8  -R 20 -P 65536 --addrlog run_h2_t7_w8.txt
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
#include <errno.h>
#include <sys/mman.h>
#ifdef __linux__
#include <sys/syscall.h>
#include <linux/perf_event.h>
#endif

static long g_pagesz = 4096;
static char *volatile g_sink; // volatile 指针对象本身：store 不可被消除（v2.1）

#define NSETS        256   // X4 TRM Table 9-32：L2 TLB entry 0-255 / way
#define NWAYS_TRUTH    8   // X4 TRM Table 5-1：8-way

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

// ---------- PMU（v2.1：fd<0 不再返回 0；带 time_enabled/time_running） ----------
typedef struct { uint64_t val, ena, run; } perf_snap_t;
#ifdef __linux__
static int perf_open(uint32_t ev) {
    struct perf_event_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.size = sizeof(attr);
    attr.type = PERF_TYPE_RAW;
    attr.config = ev;
    attr.read_format = PERF_FORMAT_TOTAL_TIME_ENABLED |
                       PERF_FORMAT_TOTAL_TIME_RUNNING; // 多路复用检测
    int fd = (int)syscall(SYS_perf_event_open, &attr, 0, -1, -1, 0);
    if (fd < 0)
        fprintf(stderr, "WARN: perf_event_open(0x%x) failed: %s —— "
                "该事件将输出 n/a（勿当作 0 refill 解读）\n",
                ev, strerror(errno));
    return fd;
}
// 返回 0 成功；-1 不可用。禁止在失败时返回 0 冒充计数（评审2-6）。
static int perf_snap(int fd, perf_snap_t *s) {
    if (fd < 0) return -1;
    uint64_t b[3];
    if (read(fd, b, sizeof(b)) != sizeof(b)) return -1;
    s->val = b[0]; s->ena = b[1]; s->run = b[2];
    return 0;
}
#else
static int perf_open(uint32_t e) { (void)e; return -1; }
static int perf_snap(int fd, perf_snap_t *s) { (void)fd; (void)s; return -1; }
#endif

static void build_chain(uintptr_t *vas, int n, char **cells) {
    for (int i = 0; i < n; i++) cells[i] = (char *)vas[i];
    for (int i = 0; i < n; i++)
        *(char **)vas[i] = (char *)vas[(i + 1) % n]; // 环形链
}

// filler 页选择与建链在 run 模式内联完成（v2.2：按候选 H 过滤目标 set +
// 独立 mmap，见 main）；此处不再保留旧版连续页 filler 构造函数。

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
    // v2.2（评审3-P0-5）：set_index 固定按 4K 粒度计算，页大小不符直接拒绝，
    // 并尽力禁用 THP（匿名大页会破坏"每页一条 4K 翻译"的前提）。
    if (g_pagesz != 4096) {
        fprintf(stderr, "FATAL: page size %ld != 4096, probe assumes 4K granule\n",
                g_pagesz);
        return 2;
    }

    char *base = mmap(NULL, total_pages * (size_t)g_pagesz,
                      PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (base == MAP_FAILED) { perror("mmap"); return 1; }
#ifdef MADV_NOHUGEPAGE
    madvise(base, total_pages * (size_t)g_pagesz, MADV_NOHUGEPAGE);
#endif

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
    // 对照组 T2（评审3-P0-3：v2.1 只解析未运行，本版实现真实第二组）
    uintptr_t *vas2 = NULL;
    if (have_T2) {
        vas2 = malloc(sizeof(uintptr_t) * (size_t)ways);
        if (collect_set_addrs(H, target2, ways, base, total_pages, vas2) < ways) {
            fprintf(stderr, "cannot collect T2 set %u under H%d\n", target2, H);
            return 1;
        }
        for (int i = 0; i < ways; i++)     // 显式无交集断言（评审3-P0-1）
            for (int j = 0; j < ways; j++)
                if (vas[i] == vas2[j]) { fprintf(stderr, "FATAL: T/T2 overlap\n"); return 3; }
        build_chain(vas2, ways, (char **)vas2);
    }
    // filler：独立 mmap（与目标映射天然不相交，评审3-P0-1），并按候选 H 过滤
    // 掉目标 set 的页（评审3-P0-2：连续 512 页在 H1 下每 set 恰占 2 页，会把目标
    // set 的竞争从 w+2 起算）；filler 散布于其余 set。>= 96 页才能驱逐 L1。
    uintptr_t *fvas_holder = NULL;
    uintptr_t fvas_first = 0;
    {
        char *fmap = mmap(NULL, (size_t)filler_pages * (size_t)g_pagesz,
                          PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (fmap == MAP_FAILED) { perror("mmap filler"); return 1; }
#ifdef MADV_NOHUGEPAGE
        madvise(fmap, (size_t)filler_pages * (size_t)g_pagesz, MADV_NOHUGEPAGE);
#endif
        // 选 filler 页：跳过 set_index == target（有 T2 时也跳过 target2）的页
        uintptr_t *tmp = malloc(sizeof(uintptr_t) * (size_t)filler_pages);
        int got_f = 0;
        for (uint64_t i = 1; got_f < filler_pages; i++) {
            uintptr_t va = (uintptr_t)fmap + i * (uint64_t)g_pagesz;
            if (set_index(H, va) == target) continue;
            if (have_T2 && set_index(H, va) == target2) continue;
            tmp[got_f++] = va;
        }
        // 随机序 + 建链
        srand(99991);
        for (int i = filler_pages - 1; i > 0; i--) {
            int j = rand() % (i + 1);
            uintptr_t t = tmp[i]; tmp[i] = tmp[j]; tmp[j] = t;
        }
        for (int i = 0; i < filler_pages; i++)
            *(char **)tmp[i] = (char *)tmp[(i + 1) % filler_pages];
        fvas_holder = tmp;
        fvas_first = tmp[0];
    }

    int fds[4];
    int mux_bad[4] = {0, 0, 0, 0};
    for (int i = 0; i < n_events; i++) fds[i] = perf_open(events[i]);
#ifdef __linux__
    for (int i = 0; i < n_events; i++) ioctl(fds[i], PERF_EVENT_IOC_RESET, 0);
    for (int i = 0; i < n_events; i++) ioctl(fds[i], PERF_EVENT_IOC_ENABLE, 0);
#endif

    uint64_t (*probe_delta)[4] = malloc(sizeof(uint64_t[4]) * rounds);  // T probe 段
    uint64_t (*probe2_delta)[4] = calloc(rounds, sizeof(uint64_t[4]));  // T2 对照段
    double *probe_ns = malloc(sizeof(double) * rounds);
    char *tp  = (char *)vas[0];
    char *tp2 = have_T2 ? (char *)vas2[0] : NULL;
    asm volatile("" ::: "memory");
    for (int r = 0; r < rounds; r++) {
        // s 数组零初始化：snap 失败时 mux 检查不读未初始化值（评审3-P0-4）
        perf_snap_t s1[4] = {{0,0,0}}, s2[4] = {{0,0,0}}, s3[4] = {{0,0,0}}, s4[4] = {{0,0,0}};
        int ok = 1;
        for (int i = 0; i < n_events; i++) ok &= (perf_snap(fds[i], &s1[i]) == 0);
        { char *p = (char *)fvas_first; for (int i = 0; i < filler_pages; i++) p = *(char *volatile *)p; } // prime
        for (int i = 0; i < n_events; i++) ok &= (perf_snap(fds[i], &s2[i]) == 0);
        double t0 = now_ns();
        for (int i = 0; i < ways; i++) tp = *(char *volatile *)tp;                    // probe T
        probe_ns[r] = now_ns() - t0;
        for (int i = 0; i < n_events; i++) ok &= (perf_snap(fds[i], &s3[i]) == 0);
        for (int i = 0; i < n_events; i++) {
            probe_delta[r][i] = ok ? s3[i].val - s2[i].val : UINT64_MAX;
            if (ok && s3[i].ena > 0 && s3[i].run * 100 < s3[i].ena * 99) mux_bad[i] = 1;
        }
        if (have_T2) {
            { char *p = (char *)fvas_first; for (int i = 0; i < filler_pages; i++) p = *(char *volatile *)p; } // 再 prime
            for (int i = 0; i < n_events; i++) ok &= (perf_snap(fds[i], &s2[i]) == 0);
            for (int i = 0; i < ways; i++) tp2 = *(char *volatile *)tp2;              // probe T2
            for (int i = 0; i < n_events; i++) ok &= (perf_snap(fds[i], &s4[i]) == 0);
            for (int i = 0; i < n_events; i++)
                probe2_delta[r][i] = ok ? s4[i].val - s2[i].val : UINT64_MAX;
        }
    }
    asm volatile("" ::: "memory");
    g_sink = have_T2 ? tp2 : tp;
#ifdef __linux__
    for (int i = 0; i < n_events; i++) ioctl(fds[i], PERF_EVENT_IOC_DISABLE, 0);
#endif

    // run 模式落盘实际使用的目标 VA（v2.1；评审3-P0-1：含 filler 不相交断言说明）
    if (addrlog) {
        FILE *out = fopen(addrlog, "w");
        for (int i = 0; i < ways; i++)
            fprintf(out, "T  0x%lx set=%u\n", (unsigned long)vas[i], set_index(H, vas[i]));
        if (have_T2)
            for (int i = 0; i < ways; i++)
                fprintf(out, "T2 0x%lx set=%u\n", (unsigned long)vas2[i], set_index(H, vas2[i]));
        fclose(out);
    }

    // 统计：剔除 round 0（含冷启动），对剩余轮取均值；报告每次目标访问的 refill 率
    printf("H%d set=%u w=%d rounds=%d filler=%d%s", H, target, ways, rounds,
           filler_pages, have_T2 ? " +T2ctrl" : "");
    for (int i = 0; i < n_events; i++) {
        if (probe_delta[1][i] == UINT64_MAX) { printf(" ev0x%x=n/a", events[i]); continue; }
        double sum = 0;
        for (int r = 1; r < rounds; r++) sum += (double)probe_delta[r][i];
        double per_round = sum / (rounds - 1);
        printf(" ev0x%x=%.1f(/round)/%.3f(/access)", events[i], per_round,
               ways > 0 ? per_round / ways : 0.0);
        if (mux_bad[i]) printf("(mux!)");
    }
    if (have_T2) {
        printf(" | T2:");
        for (int i = 0; i < n_events; i++) {
            if (probe2_delta[1][i] == UINT64_MAX) { printf(" ev0x%x=n/a", events[i]); continue; }
            double sum = 0;
            for (int r = 1; r < rounds; r++) sum += (double)probe2_delta[r][i];
            printf(" ev0x%x=%.1f", events[i], sum / (rounds - 1));
        }
    }
    { double sum = 0; for (int r = 1; r < rounds; r++) sum += probe_ns[r];
      printf(" probe_ns=%.0f", sum / (rounds - 1)); }
    printf("\n");
    printf("gate: L1D_TLB_REFILL(ev0x5) 应≈w=%d 且 L2D_TLB(ev0x2f) 应≈w；"
           "w≤%d 时 L2D_TLB_REFILL(ev0x2d) 应≈0，w≥%d 时应跳变\n", ways, NWAYS_TRUTH, NWAYS_TRUTH + 1);

    free(probe_delta); free(probe2_delta); free(probe_ns); free(vas); free(vas2); free(fvas_holder);
    return 0;
}
