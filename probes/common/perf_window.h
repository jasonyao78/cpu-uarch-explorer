// SPDX-License-Identifier: Apache-2.0
// perf_window.h — 短窗 core PMU 原子窗口（M0-3）：GROUP 启停/组读
//
// 动机（REV-TLB-R2 F5 + ROB 骨架 R2 教训）：
//   逐事件 read/enable 不保证多事件严格同窗；且 Linux GROUP read 布局为
//   { nr, time_enabled, time_running, values[nr] }——按 { nr, values[], ena, run }
//   解码会把时间增量误当事件值。本组件把布局解码做成纯函数（可合成黄金
//   测试），syscall 侧做组启停与事件→值映射（实现层次见下方"事件→值映射
//   契约"，MB-02 收口复核：不再宣称"按身份（非位置）"）。
//
// 契约：
//   - 任一成员事件打开失败 → 该事件 n/a（event_mask 置位），绝不按位置
//     顶替（R2：失败字段 n/a，不按位置替代 cycles）；
//   - 组读返回 time_enabled/time_running；mux 判定与窗口差分/有效性已具现
//     （window_delta 纯函数：enabled/running 为累计值、IOC_RESET 不清零，
//     差分跨 RESET 有效；running 差分 < enabled 差分 → mux-detected 命名
//     否决，不静默采信不完整窗口）；
//   - 显式特权级 scope（exclude_kernel/exclude_hv 可配，默认排除内核，
//     短窗协议 F5 要求内核访问不污染或少污染并显式记录）；
//   - decode_group_read 与平台无关（合成输入可测）；syscall 部分仅 Linux。
//   - 事件→值映射契约（MB-02 澄清，对齐任务书口径）：当前为**位置映射 +
//     身份表**（value_index_ 把 spec 身份映射到组内值位置）；未使用
//     PERF_FORMAT_ID/PERF_EVENT_IOC_ID，不宣称"按内核事件 ID 解码"。
#pragma once

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#ifndef __linux__
// 非 Linux：syscall 层全部 n/a（macOS 仅可编译 + decode 可测）
#define PROBE_COMMON_NO_PERF_WINDOW 1
#else
#define PROBE_COMMON_NO_PERF_WINDOW 0
#include <linux/perf_event.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#include <unistd.h>
#endif

namespace probe_common {

// ---- 纯布局解码（平台无关，合成黄金测试的直接对象） ----
//
// Linux perf_event_open GROUP + PERF_FORMAT_TOTAL_TIME_ENABLED +
// PERF_FORMAT_TOTAL_TIME_RUNNING（无 PERF_FORMAT_ID）时的 read 布局：
//   u64 nr; u64 time_enabled; u64 time_running; u64 values[nr];
// 返回是否成功；buf_words 不足时返回 false（拒绝半截解释）。
struct GroupSample {
    uint64_t nr = 0;
    uint64_t time_enabled = 0;
    uint64_t time_running = 0;
    uint64_t values[16] = {0};   // 与 kMaxEvents 一致
};
constexpr size_t kMaxEvents = 16;

inline bool decode_group_read(const uint64_t* buf, size_t buf_words,
                              size_t expect_events, GroupSample* out) {
    if (buf == nullptr || out == nullptr || buf_words < 3)
        return false;
    const uint64_t nr = buf[0];
    if (nr > kMaxEvents || buf_words < 3 + nr)
        return false;
    out->nr = nr;
    out->time_enabled = buf[1];
    out->time_running = buf[2];
    for (uint64_t i = 0; i < nr; ++i)
        out->values[i] = buf[3 + i];
    // 布局 sanity：caller 期望的事件数与组内事件数一致才可信
    // （组构成在打开时固定，read 只是采样——不一致 = 结构性错误）
    return nr == expect_events;
}

// ---- MB-05：窗口差分与有效性（纯函数，平台无关；合成黄金测试直接对象） ----
//
// Linux 语义锚点：time_enabled/time_running 自打开起累计，PERF_EVENT_IOC_RESET
// 只清零 values[] 不动时间累计——因此"前后 snapshot 差分"跨 RESET 仍成立，
// 这是窗口有效性判定的基础（差分 running < 差分 enabled = 窗口内被 mux
// 抢占，计数不完整，按 F5 纪律标记无效而不是静默采信）。
struct WindowDelta {
    uint64_t enabled_delta = 0;              // after - before（累计值单调）
    uint64_t running_delta = 0;
    uint64_t value_deltas[kMaxEvents] = {0}; // 随 RESET 清零的事件值差分
    bool valid = false;      // 正式窗口有效运行：enabled_delta > 0 且未被 mux
    bool values_monotonic = true;  // false = 窗口内发生过 RESET/重开（值差分不可靠）
    const char* reason = "ok";     // 命名否决原因（enabled-zero/mux-detected/
                                   // enabled-regressed/nr-mismatch）
};

// 两次 snapshot 差分 + 有效性判定。expect_events 与组构成一致性是结构
// 前提（nr 不符 → false，不猜）；enabled 回退（after < before）→ false
//（snapshot 不来自同一组）。值非单调不否决窗口本身（RESET 是合法操作），
// 但 values_monotonic=false 时调用方不得把 value_deltas 当窗口计数用。
inline bool window_delta(const GroupSample& before, const GroupSample& after,
                         size_t expect_events, WindowDelta* out) {
    if (out == nullptr || before.nr != after.nr || before.nr != expect_events) {
        if (out != nullptr) out->reason = "nr-mismatch";
        return false;
    }
    if (after.time_enabled < before.time_enabled) {
        out->reason = "enabled-regressed";
        return false;
    }
    out->enabled_delta = after.time_enabled - before.time_enabled;
    out->running_delta = after.time_running - before.time_running;
    for (uint64_t i = 0; i < before.nr; ++i) {
        if (after.values[i] < before.values[i])
            out->values_monotonic = false;
        out->value_deltas[i] = after.values[i] - before.values[i];
    }
    if (out->enabled_delta == 0) {
        out->valid = false;
        out->reason = "enabled-zero";
        return true;   // 结构成立但窗口没有有效运行时间
    }
    if (out->running_delta != out->enabled_delta) {
        out->valid = false;
        out->reason = "mux-detected";
        return true;   // 窗口在跑，但被多路复用抢占——计数不完整
    }
    out->valid = true;
    out->reason = "ok";
    return true;
}

// ---- Linux 原子窗口 ----
#if !PROBE_COMMON_NO_PERF_WINDOW

struct EventSpec {
    uint64_t config;          // RAW 事件号
    const char* name;         // 身份标签（record/输出用）
};

// M0-4b（TLB set 移植版）：ARM 平台 PMU type 动态（SM8650 实测 type=8），
// 非 PERF_TYPE_RAW 事件走此结构；open_typed() 与 open() 共享同一实现。
struct TypedEventSpec {
    const char* name;
    uint64_t type;            // perf_event_attr.type（如 ARM core PMU = 8）
    uint64_t config;          // RAW 事件号
};

class PerfWindow {
public:
    PerfWindow() = default;
    PerfWindow(const PerfWindow&) = delete;
    PerfWindow& operator=(const PerfWindow&) = delete;  // MB-05：单一所有权
    // MB-05：正确转移语义（评审"删除或提供正确转移语义"双选项的完整版）——
    // 搬迁后源对象清空，析构不重复 close。
    PerfWindow(PerfWindow&& other) noexcept { steal_from(other); }
    PerfWindow& operator=(PerfWindow&& other) noexcept {
        if (this != &other) { close_all(); steal_from(other); }
        return *this;
    }
    ~PerfWindow() { close_all(); }

    // exclude_kernel/exclude_hv 显式特权级 scope（F5：短窗协议要求显式记录）
    bool open(const EventSpec* specs, size_t n,
              bool exclude_kernel = true, bool exclude_hv = true) {
        if (n == 0 || n > kMaxEvents || opened_)
            return false;
        TypedEventSpec typed[kMaxEvents];
        for (size_t i = 0; i < n; ++i)
            typed[i] = {specs[i].name, PERF_TYPE_RAW, specs[i].config};
        return open_typed(typed, n, exclude_kernel, exclude_hv);
    }

    // M0-4b：带显式 PMU type 的打开（ARM 平台 type 动态，SM8650 core PMU = 8）。
    // 实现本体：open() 仅是把 RAW 事件转译后落入此处。
    bool open_typed(const TypedEventSpec* specs, size_t n,
                    bool exclude_kernel = true, bool exclude_hv = true) {
        if (n == 0 || n > kMaxEvents || opened_)
            return false;
        exclude_kernel_ = exclude_kernel;
        exclude_hv_ = exclude_hv;
        names_.assign(n, "?");        // MB-02：名称按原始 spec 身份全程占位
        for (size_t i = 0; i < n; ++i)
            names_[i] = specs[i].name ? specs[i].name : "?";
        failed_.assign(n, false);
        value_index_.assign(n, -1);   // spec 下标 → values[] 位置（-1 = n/a）
        int leader = -1;
        size_t opened = 0;
        for (size_t i = 0; i < n; ++i) {
            perf_event_attr pe;
            memset(&pe, 0, sizeof(pe));
            pe.size = sizeof(pe);
            pe.type = static_cast<uint32_t>(specs[i].type);
            pe.config = specs[i].config;
            pe.disabled = (leader < 0);
            pe.exclude_kernel = exclude_kernel_ ? 1 : 0;
            pe.exclude_hv = exclude_hv_ ? 1 : 0;
            pe.read_format = PERF_FORMAT_GROUP |
                             PERF_FORMAT_TOTAL_TIME_ENABLED |
                             PERF_FORMAT_TOTAL_TIME_RUNNING;
            const int fd = (int)syscall(SYS_perf_event_open, &pe, 0, -1,
                                        leader, 0);
            if (fd < 0) { failed_[i] = true; continue; }   // 身份制 n/a
            value_index_[i] = (int)opened++;
            if (leader < 0) leader = fd;
            else (void)ioctl(fd, PERF_EVENT_IOC_SET_OUTPUT, leader);
            fds_.push_back(fd);
        }
        if (leader < 0) return false;   // 全失败
        leader_ = leader;
        opened_ = true;
        return true;
    }

    bool enable() {
        return opened_ && ioctl(leader_, PERF_EVENT_IOC_ENABLE, 0) == 0;
    }
    bool disable() {
        return opened_ && ioctl(leader_, PERF_EVENT_IOC_DISABLE, 0) == 0;
    }

    // MB-05：snapshot 解码与窗口解释分离——read_snapshot 只做结构解码；
    // 差分/有效性判定走纯函数 window_delta()（可合成测试，不依赖内核）。
    bool read_snapshot(GroupSample* out) {
        if (!opened_ || out == nullptr) { last_error_ = "not-opened"; return false; }
        uint64_t buf[3 + kMaxEvents] = {0};
        const ssize_t got = ::read(leader_, buf, sizeof(buf));
        if (got < 0) { last_error_ = "read:syscall"; return false; }
        if (got == 0 || (got % 8) != 0) {
            last_error_ = "read:partial-or-unaligned";
            return false;
        }
        const size_t words = (size_t)got / 8;
        if (words < 3) { last_error_ = "read:too-short"; return false; }
        if (!decode_group_read(buf, words, fds_.size(), out)) {
            last_error_ = "read:nr-mismatch-or-truncated";
            return false;
        }
        return true;
    }

    // 组读 + 按身份解码 + mux 旗标（兼容 read() = read_snapshot + 身份掩码
    // + mux 旗标的便捷组合；窗口差分/有效性请用 read_snapshot + window_delta）。
    // MB-01：read 有效载荷 = (3 + 实际组内事件数)×8 字节，随成功打开的
    // 事件数变化——按实际返回字节判定（最低长度/8 对齐/nr/组构成），
    // 不以最大容量判定完整性。
    bool read(GroupSample* out, bool* ok_mask, bool* mux_flag) {
        if (!read_snapshot(out)) return false;
        if (ok_mask) {
            for (size_t i = 0; i < failed_.size(); ++i)
                ok_mask[i] = !failed_[i];
        }
        if (mux_flag)
            *mux_flag = out->time_running != out->time_enabled;
        return true;
    }

    // 事件身份 → values[] 下标（-1 = 该事件打开失败，n/a）
    int value_index(size_t spec_i) const { return value_index_.at(spec_i); }
    // 上次 read/open 的命名失败原因（MB-01：截断/nr 不符/syscall 失败
    // 保留明确原因，不静默 false）。
    const char* last_error() const { return last_error_.c_str(); }
    size_t event_count() const { return failed_.size(); }
    const std::string& name(size_t i) const { return names_.at(i); }
    bool failed(size_t i) const { return failed_.at(i); }
    bool exclude_kernel() const { return exclude_kernel_; }
    bool exclude_hv() const { return exclude_hv_; }

    void steal_from(PerfWindow& other) {
        fds_ = std::move(other.fds_);
        names_ = std::move(other.names_);
        failed_ = std::move(other.failed_);
        value_index_ = std::move(other.value_index_);
        leader_ = other.leader_;
        opened_ = other.opened_;
        exclude_kernel_ = other.exclude_kernel_;
        exclude_hv_ = other.exclude_hv_;
        last_error_ = std::move(other.last_error_);
        other.leader_ = -1;
        other.opened_ = false;
    }

    void close_all() {
        for (int fd : fds_) close(fd);
        fds_.clear();
        names_.clear();
        failed_.clear();
        value_index_.clear();
        leader_ = -1;
        opened_ = false;
    }

private:
    std::vector<int> fds_;
    std::vector<std::string> names_;
    std::vector<bool> failed_;
    std::vector<int> value_index_;
    int leader_ = -1;
    bool opened_ = false;
    bool exclude_kernel_ = true;
    bool exclude_hv_ = true;
    std::string last_error_;
};

#else  // 非 Linux 桩：可编译，全部 n/a

struct EventSpec { uint64_t config; const char* name; };
class PerfWindow {
public:
    bool open(const EventSpec*, size_t, bool = true, bool = true) {
        fprintf(stderr, "note: PerfWindow n/a on this platform\n");
        return false;
    }
    bool enable() { return false; }
    bool disable() { return false; }
    bool read_snapshot(GroupSample*) { return false; }
    bool read(GroupSample*, bool*, bool*) { return false; }
};

#endif

} // namespace probe_common
