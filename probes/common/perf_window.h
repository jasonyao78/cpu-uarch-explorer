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
//   - 组读返回 time_enabled/time_running；mux 判定（running != enabled）
//     已具现，窗口时间差分/有效性 API 尚未交付（MB-05 窗口有效性后置）；
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

// ---- Linux 原子窗口 ----
#if !PROBE_COMMON_NO_PERF_WINDOW

struct EventSpec {
    uint64_t config;          // RAW 事件号
    const char* name;         // 身份标签（record/输出用）
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
            pe.type = PERF_TYPE_RAW;
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

    // 组读 + 按身份解码。成员打开失败的位在 ok_mask 中置 false。
    // MB-01：read 有效载荷 = (3 + 实际组内事件数)×8 字节，随成功打开的
    // 事件数变化——按实际返回字节判定（最低长度/8 对齐/nr/组构成），
    // 不以最大容量判定完整性。
    bool read(GroupSample* out, bool* ok_mask, bool* mux_flag) {
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
    bool read(GroupSample*, bool*, bool*) { return false; }
};

#endif

} // namespace probe_common
