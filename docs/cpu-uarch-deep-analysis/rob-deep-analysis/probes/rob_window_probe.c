/*
 * rob_window_probe.c — Cortex-X4 ROB 窗口协议探针（骨架 v0.1）
 *
 * 对应《ROB微架构深度分析报告》§5.4（E1/E2 协议）：
 *   模式 A：miss 锚点 —— [ldr x0,[x0]] + N×filler + [ldr x1,[x1]] + 循环控制
 *   模式 C：fsqrt 链锚点（pattern.c 路线）—— 8×fsqrt d0,d0 + N×filler + 循环控制
 *
 * 工程路线（报告 §5.1-2）：被测指令序列由本文件的手写发射器生成（mini-JIT），
 * 编译器不接触测量循环 —— 防优化纪律（矩阵 B5）由构造保证，配合 --write-asm
 * 生成黄金汇编回归（robsize check-gold.sh 同款，见 README）。
 *
 * 版本记录：
 *   v0.1 (2026-09-29) 初版：7 个填充类别 × 2 锚点模式；入口对齐抖动；
 *        Linux perf RAW 事件组（CPU_CYCLES/INST_SPEC/INST_RETIRED 默认集）；
 *        逐轮 rawlog；macOS 可编译冒烟（PMU 通道自动 n/a）。
 *        骨架性质：无统计检验、无 DVFS 记录、chase 回路完整性未校验 —— 见 README TODO。
 *
 * 许可证：Apache-2.0（cpu-uarch-explorer 仓库）。设计继承 stuffedcow/robsize/pattern.c
 * 三家的公开思路，全部代码重写，未复制上述仓库源码。
 */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <getopt.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/mman.h>

#ifdef __APPLE__
#include <pthread.h>
#include <libkern/OSCacheControl.h>
#else
#include <linux/perf_event.h>
#include <sched.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#endif

/* ---------------- AArch64 发射器（全部编码经 objdump 核验，见 README） ---------------- */

typedef uint32_t insn_t;

/* 基址取自 ARM Architecture Reference Manual A64 编码；寄存器字段可轮转 */
#define A64_NOP        0xD503201Fu
#define A64_RET        0xD65F03C0u
#define E_ADD(d, n, m)  (0x8B000000u | ((m) << 16) | ((n) << 5) | (d))
#define E_ORR_MOV(d, m) (0xAA0003E0u | ((m) << 16) | (d))          /* mov xd, xm = orr xd, xzr, xm */
#define E_MOVZ(d, imm)  (0xD2800000u | (((imm) & 0xFFFFu) << 5) | (d))
#define E_MOVK(d, imm, s)(0xF2800000u | (((imm) & 0xFFFFu) << 5) | (((s) / 16) << 21) | (d))
#define E_FADD(d, n, m) (0x1E202800u | ((m) << 16) | ((n) << 5) | (d))
#define E_FSQRT(d, n)   (0x1E61C000u | ((n) << 5) | (d))
#define E_LDR_UOFF(t, n, off_bytes) (0xF9400000u | ((((off_bytes) >> 3) & 0xFFFu) << 10) | ((n) << 5) | (t))
#define E_LDR(t, n)     E_LDR_UOFF(t, n, 0)
#define E_STR_UOFF(t, n, off_bytes) (0xF9000000u | ((((off_bytes) >> 3) & 0xFFFu) << 10) | ((n) << 5) | (t))
#define E_SUBS_IMM(d, n, imm)  (0xF1000000u | (((imm) & 0xFFFu) << 10) | ((n) << 5) | (d))
#define E_BNE(imm19)    (0x54000001u | (((imm19) & 0x7FFFFu) << 5))
#define E_FMOV_DI(d)    (0x9E6703E0u | (d))

typedef struct { insn_t *buf; size_t pos, cap; } emitter_t;

static void emit(emitter_t *e, insn_t w) {
    assert(e->pos < e->cap);
    e->buf[e->pos++] = w;
}

/* movz/movk 链装载 64 位立即数（地址类常量） */
static void emit_mov_imm64(emitter_t *e, unsigned rd, uint64_t v) {
    emit(e, E_MOVZ(rd, (unsigned)(v & 0xFFFFu)));
    for (unsigned s = 16; s < 64; s += 16)
        emit(e, E_MOVK(rd, (unsigned)((v >> s) & 0xFFFFu), s));
}

/* 填充类别：与报告 §5.5 类别矩阵对应 */
typedef enum { C_NOP = 0, C_ADD, C_MOVI, C_MOVR, C_FADD, C_LDR, C_STR, C_COUNT } fill_class_t;

static const struct { const char *name; int needs_comp; } kClass[C_COUNT] = {
    [C_NOP]  = { "nop",  1 },   /* 仅占窗口条目（E0-3 前提，主协议前必须验证） */
    [C_ADD]  = { "add",  1 },   /* + INT PRF（目的寄存器） */
    [C_MOVI] = { "movi", 1 },   /* + rename 消除配额（E0-2） */
    [C_MOVR] = { "movr", 1 },   /* + rename 消除（E0-1） */
    [C_FADD] = { "fadd", 0 },   /* NO_COMP：不与锚点 load 争用（FP PRF） */
    [C_LDR]  = { "ldr",  1 },   /* + Load buffer */
    [C_STR]  = { "str",  1 },   /* + Store buffer（1 MOP = SA+SD 2 µOP） */
};

static void emit_filler(emitter_t *e, fill_class_t c, unsigned i, uint64_t hot) {
    unsigned rd = 4 + (i & 7u);   /* 目的寄存器轮转 x4..x11 / s0..s7 */
    switch (c) {
    case C_NOP:  emit(e, A64_NOP); break;
    case C_ADD:  emit(e, E_ADD(rd, 16, 17)); break;
    case C_MOVI: emit(e, E_MOVZ(rd, 1)); break;
    case C_MOVR: emit(e, E_ORR_MOV(rd, 16)); break;
    case C_FADD: emit(e, E_FADD(i & 7u, 16, 17)); break;
    case C_LDR:  emit(e, E_LDR_UOFF(rd, 12, (i & 7u) * 8)); break;   /* 热缓冲命中 */
    case C_STR:  emit(e, E_STR_UOFF(13, 12, (i & 7u) * 8)); break;
    default: assert(!"bad class");
    }
    (void)hot;
}

typedef enum { ANCHOR_MISS = 0, ANCHOR_FSQRT } anchor_mode_t;

/*
 * 生成测量例程（无参调用；迭代计数烘焙进代码，每次调用自重装）。
 * 布局：[NOP 着陆区 64B] → [mov 常量] → 16B 对齐 → loop: 锚点 + N×filler
 *       (+第二锚点) + subs/b.ne → ret。
 * 入口抖动（i%4×16B）只落入开头的 NOP 区——无论哪个偏移进入，常量区总会执行
 * （robsize 的 prologue-first 结构；v0.1 冒烟实测：入口放常量区之后会跳过
 * x2 计数器装载，用调用方残留值死循环）。
 */
#define LANDING_NOPS 16   /* 16 条 NOP = 64B = 4 个 16B 抖动入口 */

static size_t build_routine(insn_t *buf, size_t cap, fill_class_t cls, anchor_mode_t amode,
                            unsigned icount, uint64_t its, uint64_t chase_a, uint64_t chase_b,
                            uint64_t hot) {
    emitter_t e = { buf, 0, cap };
    const int comp = kClass[cls].needs_comp;
    const int adj = (int)icount - (comp ? 2 : 0);
    if (adj < 0) { fprintf(stderr, "icount too small for class %s\n", kClass[cls].name); exit(2); }

    /* 着陆区（抖动入口；任何 16B 偏移落入都只会少执行几条 NOP） */
    for (int k = 0; k < LANDING_NOPS; k++) emit(&e, A64_NOP);

    /* 常量装载（循环外，每次调用必经） */
    emit_mov_imm64(&e, 2, its);                                  /* x2 = 迭代计数 */
    if (amode == ANCHOR_MISS) {
        emit_mov_imm64(&e, 0, chase_a);   /* x0 = chase A */
        emit_mov_imm64(&e, 1, chase_b);   /* x1 = chase B */
    }
    if (cls == C_ADD || cls == C_MOVR) { emit_mov_imm64(&e, 16, 0x1111); emit_mov_imm64(&e, 17, 0x2222); }
    if (cls == C_FADD) { emit(&e, E_FMOV_DI(16)); emit(&e, E_FMOV_DI(17)); }
    if (cls == C_LDR || cls == C_STR) { emit_mov_imm64(&e, 12, hot); emit_mov_imm64(&e, 13, 0x1234); }

    while ((e.pos & 3u) != 0) emit(&e, A64_NOP);         /* 16B 对齐 */
    const size_t loop_start = e.pos;

    if (amode == ANCHOR_MISS) {
        emit(&e, E_LDR(0, 0));                            /* L₁: ldr x0,[x0] */
        for (int j = 0; j < adj; j++) emit_filler(&e, cls, (unsigned)j, hot);
        emit(&e, E_LDR(1, 1));                            /* L₂: ldr x1,[x1] */
    } else {
        for (int k = 0; k < 8; k++) emit(&e, E_FSQRT(0, 0));  /* 链式 fsqrt d0,d0 ×8 */
        for (int j = 0; j < adj; j++) emit_filler(&e, cls, (unsigned)j, hot);
    }
    /* 循环控制（其窗口占用按未公开处理 → §5.8 判据 J7 的 ±2 口径带） */
    emit(&e, E_SUBS_IMM(2, 2, 1));                        /* subs x2, x2, #1 */
    const long off = (long)loop_start - (long)e.pos;      /* b.ne 以自身地址为基准 */
    emit(&e, E_BNE((unsigned)(off >> 2)));
    emit(&e, A64_RET);
    return e.pos;
}

/* ---------------- 计时与 PMU（Linux；macOS 仅墙钟） ---------------- */

static uint64_t ns_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}

#define MAX_EV 8
#ifndef __APPLE__
typedef struct { int fd; const char *name; } ev_t;

static int perf_open_raw(uint64_t evcode, int group_fd, int read_format) {
    struct perf_event_attr pe;
    memset(&pe, 0, sizeof(pe));
    pe.size = sizeof(pe);
    pe.type = PERF_TYPE_RAW;
    pe.config = evcode;
    pe.disabled = (group_fd < 0);
    pe.read_format = (uint64_t)read_format;
    return (int)syscall(SYS_perf_event_open, &pe, 0, -1, group_fd, 0);
}

/* 组读布局：nr, values[nr], time_enabled, time_running */
typedef struct { uint64_t nr, val[MAX_EV], ena, run; } group_t;

static int g_ev_count = 0;
static ev_t g_ev[MAX_EV];
static int g_read_format;

static void perf_setup(uint64_t *codes, int n, const char **names) {
    g_read_format = PERF_FORMAT_GROUP | PERF_FORMAT_TOTAL_TIME_ENABLED | PERF_FORMAT_TOTAL_TIME_RUNNING;
    int leader = -1;
    for (int i = 0; i < n; i++) {
        int fd = perf_open_raw(codes[i], leader, g_read_format);
        if (fd < 0) {
            fprintf(stderr, "warn: perf_event_open 0x%" PRIx64 " failed (%s) — 该事件记 n/a\n",
                    codes[i], strerror(errno));
            continue;                      /* TLB 评审2 教训：失败即 n/a，不伪报 0 */
        }
        if (leader < 0) leader = fd;
        else ioctl(fd, PERF_EVENT_IOC_SET_OUTPUT, leader);
        g_ev[g_ev_count].fd = fd; g_ev[g_ev_count].name = names[i]; g_ev_count++;
    }
    if (leader >= 0) ioctl(leader, PERF_EVENT_IOC_ENABLE, 0);
}

static void perf_read_group(group_t *g) {
    memset(g, 0, sizeof(*g));
    if (g_ev_count == 0) return;
    ssize_t want = (ssize_t)(sizeof(uint64_t) * (1 + (size_t)g_ev_count + 2));
    if (read(g_ev[0].fd, g, (size_t)want) != want) {
        fprintf(stderr, "warn: perf group read failed (%s) — 本轮事件记 n/a\n", strerror(errno));
        memset(g, 0, sizeof(*g));
    }
}
#else
typedef struct { uint64_t nr, val[MAX_EV], ena, run; } group_t;
typedef struct { int fd; const char *name; } ev_t;
static int g_ev_count = 0;
static ev_t g_ev[MAX_EV];
static void perf_setup(uint64_t *codes, int n, const char **names) {
    (void)codes; (void)n; (void)names;
    fprintf(stderr, "note: macOS 无 perf_event_open，PMU 通道 n/a（仅墙钟）\n");
}
static void perf_read_group(group_t *g) { memset(g, 0, sizeof(*g)); }
#endif

/* ---------------- chase 缓冲（miss 锚点）：长循环 + 远跳，保证每轮 miss ---------------- */

static void chase_init(uint64_t *p, size_t n, size_t cycle_len) {
    for (size_t i = 0; i < n; i++) p[i] = (uint64_t)&p[i + 1];
    p[n - 1] = (uint64_t)&p[0];
    srand(42);
    for (size_t i = n - 1; i > 0; i--) {                 /* robsize init_dbuf 同款随机化 */
        if (i & 0x1ffu) continue;
        if (i < cycle_len) continue;
        size_t k = (size_t)rand() % (i / cycle_len) * cycle_len + (i % cycle_len);
        uint64_t t = p[i]; p[i] = p[k]; p[k] = t;
    }
}

/* ---------------- main ---------------- */

static void usage(const char *p) {
    fprintf(stderr,
        "usage: %s -t <class> -n <icount> [options]\n"
        "  -t class    nop|add|movi|movr|fadd|ldr|str\n"
        "  -n N        填充指令数（类别含补偿：实际发射 N-2 或 N，见 README）\n"
        "  -a mode     miss（默认，A 档）| fsqrt（C 档链锚点）\n"
        "  -i its      内层迭代次数（默认 262144；J1 门控：walk 足迹 = its×8B 必须超 L2）\n"
        "  -r outer    外层重复轮数（默认 30）\n"
        "  -e hex      追加 RAW PMU 事件（可重复；默认集 0x11,0x1B,0x8）\n"
        "  -m mb       chase 缓冲区大小 MB（默认 128，仅 miss 模式）\n"
        "  -l n        chase 远跳间隔（默认 1024 步）\n"
        "  --rawlog f  逐轮原始数据 CSV\n"
        "  --write-asm f  生成机器码到文件（黄金回归用），不运行\n"
        "  --no-jitter 关闭入口对齐抖动\n"
        "  --pin cpu   绑核（Linux；失败即退出——TLB 评审2 教训）\n", p);
    exit(2);
}

int main(int argc, char **argv) {
    const char *cls_name = NULL, *rawlog = NULL, *write_asm = NULL;
    unsigned icount = 0, its = 262144, outer = 30, mem_mb = 128, cycle_len = 1024;
    int pin = -1; bool jitter = true; anchor_mode_t amode = ANCHOR_MISS;
    uint64_t extra[MAX_EV]; int extra_n = 0;

    static const struct option lo[] = {
        {"rawlog", required_argument, NULL, 1}, {"write-asm", required_argument, NULL, 2},
        {"no-jitter", no_argument, NULL, 3}, {"pin", required_argument, NULL, 4}, {NULL, 0, NULL, 0}};
    int ch;
    while ((ch = getopt_long(argc, argv, "t:n:a:i:r:e:m:h", lo, NULL)) != -1) {
        switch (ch) {
        case 't': cls_name = optarg; break;
        case 'n': icount = (unsigned)atoi(optarg); break;
        case 'a': amode = (strcmp(optarg, "fsqrt") == 0) ? ANCHOR_FSQRT : ANCHOR_MISS; break;
        case 'i': its = (unsigned)atoi(optarg); break;
        case 'r': outer = (unsigned)atoi(optarg); break;
        case 'e': extra[extra_n++] = strtoull(optarg, NULL, 0); break;
        case 'm': mem_mb = (unsigned)atoi(optarg); break;
        case 'l': cycle_len = (unsigned)atoi(optarg); break;
        case 1: rawlog = optarg; break;
        case 2: write_asm = optarg; break;
        case 3: jitter = false; break;
        case 4: pin = atoi(optarg); break;
        default: usage(argv[0]);
        }
    }
    if (!cls_name || icount == 0) usage(argv[0]);
    fill_class_t cls = C_COUNT;
    for (int c = 0; c < C_COUNT; c++) if (strcmp(cls_name, kClass[c].name) == 0) cls = (fill_class_t)c;
    if (cls == C_COUNT) { fprintf(stderr, "unknown class %s\n", cls_name); usage(argv[0]); }
    if (icount > 1024) { fprintf(stderr, "icount > 1024 超出骨架设计上限\n"); return 2; }

#ifndef __APPLE__
    if (pin >= 0) {
        cpu_set_t s; CPU_ZERO(&s); CPU_SET(pin, &s);
        if (sched_setaffinity(0, sizeof(s), &s) != 0) {
            fprintf(stderr, "error: 绑核 cpu%d 失败 (%s)\n", pin, strerror(errno)); return 1;
        }
    }
#else
    if (pin >= 0) fprintf(stderr, "warn: --pin 仅 Linux 生效，忽略\n");
    (void)pin;
#endif

    /* 常量区与缓冲 */
    const uint64_t kCodeBytes = 1u << 20;
    insn_t *code = mmap(NULL, kCodeBytes, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (code == MAP_FAILED) { perror("mmap code"); return 1; }
    uint64_t chase_a = 0, chase_b = 0, hot = 0;
    uint64_t *chase = NULL;
    if (amode == ANCHOR_MISS) {
        size_t bytes = (size_t)mem_mb << 20;
        chase = mmap(NULL, bytes, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (chase == MAP_FAILED) { perror("mmap chase"); return 1; }
#ifndef __APPLE__
        madvise(chase, bytes, MADV_NOHUGEPAGE);   /* 页粒度控制（TLB 项目教训：显式固定） */
#endif
        size_t n = bytes / sizeof(uint64_t) / 2;
        chase_init(chase, n, cycle_len); chase_init(chase + n, n, cycle_len);
        chase_a = (uint64_t)chase; chase_b = (uint64_t)(chase + n);
    }
    uint64_t *hotbuf = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (hotbuf == MAP_FAILED) { perror("mmap hotbuf"); return 1; }
    memset(hotbuf, 1, 4096);
    hot = (uint64_t)hotbuf;

    const size_t ninsn = build_routine(code, kCodeBytes / sizeof(insn_t), cls, amode, icount, its,
                                       chase_a, chase_b, hot);
    const size_t code_bytes = ninsn * sizeof(insn_t);

    if (write_asm) {
        FILE *f = fopen(write_asm, "wb");
        if (!f || fwrite(code, code_bytes, 1, f) != 1) { perror("write-asm"); return 1; }
        fclose(f);
        fprintf(stderr, "wrote %zu bytes of generated code to %s\n", code_bytes, write_asm);
        fprintf(stderr, "inspect: objdump -D -b binary -m aarch64 %s\n", write_asm);
        return 0;
    }

#ifdef __APPLE__
    pthread_jit_write_protect_np(false);
    sys_icache_invalidate(code, code_bytes);
    pthread_jit_write_protect_np(true);
    if (mprotect(code, kCodeBytes, PROT_READ | PROT_EXEC) != 0) { perror("mprotect"); return 1; }
#else
    __clear_cache((char *)code, (char *)code + code_bytes);
    if (mprotect(code, kCodeBytes, PROT_READ | PROT_EXEC) != 0) { perror("mprotect"); return 1; }
#endif

    /* PMU 默认集 + 用户追加 */
    static uint64_t codes[MAX_EV]; static const char *names[MAX_EV]; int n_ev = 0;
    if (g_ev_count == 0) { /* perf_setup 只调一次 */
        codes[n_ev] = 0x11; names[n_ev++] = "CPU_CYCLES";
        codes[n_ev] = 0x1B; names[n_ev++] = "INST_SPEC";
        codes[n_ev] = 0x8;  names[n_ev++] = "INST_RETIRED";
        for (int i = 0; i < extra_n && n_ev < MAX_EV; i++) { codes[n_ev] = extra[i]; names[n_ev++] = "raw"; }
    }
    perf_setup(codes, n_ev, names);

    FILE *rf = NULL;
    if (rawlog) {
        rf = fopen(rawlog, "w");
        if (!rf) { perror("rawlog"); return 1; }
        fprintf(rf, "round,jit_off,ns_total");
        for (int i = 0; i < g_ev_count; i++) fprintf(rf, ",%s", g_ev[i].name);
        fprintf(rf, "\n");
    }

    printf("# class=%s anchor=%s n=%u its=%u outer=%u comp=%d\n",
           kClass[cls].name, amode == ANCHOR_MISS ? "miss" : "fsqrt", icount, its, outer,
           kClass[cls].needs_comp);
    printf("# per_chunk_ns_min\tper_chunk_ns_avg\tper_chunk_cycles_avg\n");

    double sum_ns = 0, min_ns = 1e30;
    uint64_t sum_cyc = 0; unsigned used_rounds = 0;
    for (unsigned i = 0; i < outer; i++) {
        /* 入口抖动：只落入开头 64B NOP 着陆区内的 16B 偏移（常量区在其后必经） */
        const size_t off_bytes = jitter ? ((i % 4u) * 16u) : 0;
        void (*routine)(void) = (void (*)(void))(void *)((char *)code + off_bytes);
        routine();                                             /* warmup */

        group_t g0, g1; perf_read_group(&g0);
        const uint64_t t0 = ns_now();
        routine();
        const uint64_t t1 = ns_now();
        perf_read_group(&g1);

        const double ns = (double)(t1 - t0);
        const uint64_t cyc = (g1.nr >= 1 && g0.nr >= 1) ? g1.val[0] - g0.val[0] : 0;
        const double per_chunk = ns / (double)its;
        if (per_chunk < min_ns) min_ns = per_chunk;
        sum_ns += per_chunk; sum_cyc += cyc; used_rounds++;
        if (rf) {
            fprintf(rf, "%u,%zu,%.0f", i, off_bytes, ns);
            for (int k = 0; k < g_ev_count && (size_t)k < g1.nr; k++)
                fprintf(rf, ",%" PRIu64, g1.val[k] - g0.val[k]);
            fprintf(rf, "\n");
        }
        volatile uint64_t sink = (chase ? chase[0] : 0) ^ hotbuf[0];  /* 触碰结果，防 LTO 整段消除 */
        (void)sink;
    }
    printf("%.2f\t%.2f\t%.2f\n", min_ns, sum_ns / (double)used_rounds,
           g_ev_count ? (double)sum_cyc / (double)used_rounds / (double)its : 0.0);
    if (rf) fclose(rf);
    return 0;
}
