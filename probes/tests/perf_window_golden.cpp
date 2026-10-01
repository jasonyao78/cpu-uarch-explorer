// SPDX-License-Identifier: Apache-2.0
// perf_window 黄金测试（M0-3）：合成 GROUP read 布局解码断言。
// 直接对象 = decode_group_read 纯函数（平台无关）；场景钉住 ROB 骨架 R2
// 的教训——{nr,ena,run,values[]} 被误按 {nr,values[],ena,run} 解读时
// 时间增量会被当成事件值。
#include <cstdint>
#include <cstdio>
#include <cstring>

#include "perf_window.h"

namespace pc = probe_common;

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (!(cond)) { std::fprintf(stderr, "FAIL: %s\n", msg); ++failures; } \
} while (0)

int main() {
    // 场景 1：评审 R2 的合成输入 [3, 1000, 1000, 111, 222, 333]
    // 正确解码：ena=1000 run=1000 values={111,222,333}
    // 旧错误布局会得到 "values"={1000,1000,111}——本测试钉死正确布局。
    {
        const uint64_t buf[] = {3, 1000, 1000, 111, 222, 333};
        pc::GroupSample s;
        CHECK(pc::decode_group_read(buf, 6, 3, &s), "R2 synthetic decodes");
        CHECK(s.time_enabled == 1000 && s.time_running == 1000,
              "enabled/running at fixed positions");
        CHECK(s.values[0] == 111 && s.values[1] == 222 && s.values[2] == 333,
              "values follow nr,ena,run (not nr,values,ena,run)");
    }
    // 场景 2：多路复用窗口（running < enabled）原样暴露，不静默
    {
        const uint64_t buf[] = {2, 2000, 1500, 77, 88};
        pc::GroupSample s;
        CHECK(pc::decode_group_read(buf, 5, 2, &s), "mux window decodes");
        CHECK(s.time_running == 1500 && s.values[1] == 88, "mux fields exact");
    }
    // 场景 3：半截缓冲拒绝（buf_words 不足 → false，拒绝半截解释）
    {
        const uint64_t buf[] = {3, 1000, 1000, 111};
        pc::GroupSample s;
        CHECK(!pc::decode_group_read(buf, 4, 3, &s), "truncated buffer rejected");
    }
    // 场景 4：事件数与期望不符 → false（结构性错误，不猜）
    {
        const uint64_t buf[] = {2, 1000, 1000, 111, 222};
        pc::GroupSample s;
        CHECK(!pc::decode_group_read(buf, 5, 3, &s), "nr mismatch rejected");
    }
    // 场景 5：超大 nr 拒绝（防越界）
    {
        const uint64_t buf[] = {99, 1000, 1000, 111};
        pc::GroupSample s;
        CHECK(!pc::decode_group_read(buf, 4, 99, &s), "oversize nr rejected");
    }

    // ---- MB-05：window_delta 窗口差分/有效性（纯函数，平台无关） ----
    // 场景 6：有效窗口（enabled==running 同步增长）→ valid，差分精确
    {
        pc::GroupSample before{}, after{};
        before.nr = after.nr = 2;
        before.time_enabled = 1000; before.time_running = 1000;
        before.values[0] = 10; before.values[1] = 20;
        after.time_enabled = 1500; after.time_running = 1500;
        after.values[0] = 60; after.values[1] = 45;
        pc::WindowDelta d;
        CHECK(pc::window_delta(before, after, 2, &d), "valid window delta ok");
        CHECK(d.valid && std::strcmp(d.reason, "ok") == 0, "valid window flagged");
        CHECK(d.enabled_delta == 500 && d.running_delta == 500,
              "enabled/running deltas exact");
        CHECK(d.value_deltas[0] == 50 && d.value_deltas[1] == 25,
              "value deltas exact");
        CHECK(d.values_monotonic, "monotonic values without RESET");
    }
    // 场景 7：mux 窗口（running 差分 < enabled 差分）→ valid=false 命名否决
    {
        pc::GroupSample before{}, after{};
        before.nr = after.nr = 1;
        before.time_enabled = 2000; before.time_running = 2000;
        before.values[0] = 7;
        after.time_enabled = 2600; after.time_running = 2300;
        after.values[0] = 99;
        pc::WindowDelta d;
        CHECK(pc::window_delta(before, after, 1, &d), "mux window structurally ok");
        CHECK(!d.valid && std::strcmp(d.reason, "mux-detected") == 0,
              "mux window named rejection");
        CHECK(d.enabled_delta == 600 && d.running_delta == 300,
              "mux deltas exact");
    }
    // 场景 8：窗口内 RESET（values 回退、enabled 仍单调）→ valid 保留、
    // values_monotonic=false（值差分不得当窗口计数用）
    {
        pc::GroupSample before{}, after{};
        before.nr = after.nr = 1;
        before.time_enabled = 3000; before.time_running = 3000;
        before.values[0] = 500;
        after.time_enabled = 3400; after.time_running = 3400;
        after.values[0] = 40;   // RESET 清零后重新累计
        pc::WindowDelta d;
        CHECK(pc::window_delta(before, after, 1, &d), "RESET window structurally ok");
        CHECK(d.valid && std::strcmp(d.reason, "ok") == 0,
              "RESET does not invalidate window time basis");
        CHECK(!d.values_monotonic, "RESET values flagged non-monotonic");
    }
    // 场景 9：零长窗口（enabled 差分 = 0）→ valid=false enabled-zero
    {
        pc::GroupSample before{}, after{};
        before.nr = after.nr = 1;
        before.time_enabled = 4000; before.time_running = 4000;
        after.time_enabled = 4000; after.time_running = 4000;
        pc::WindowDelta d;
        CHECK(pc::window_delta(before, after, 1, &d), "zero window structural ok");
        CHECK(!d.valid && std::strcmp(d.reason, "enabled-zero") == 0,
              "zero-length window named rejection");
    }
    // 场景 10：enabled 回退（snapshot 不来自同一组）→ false 命名否决
    {
        pc::GroupSample before{}, after{};
        before.nr = after.nr = 1;
        before.time_enabled = 5000; after.time_enabled = 1000;
        pc::WindowDelta d;
        CHECK(!pc::window_delta(before, after, 1, &d),
              "enabled regression rejected");
        CHECK(std::strcmp(d.reason, "enabled-regressed") == 0,
              "enabled regression named");
    }
    // 场景 11：组构成不一致（nr 不符）→ false，不猜
    {
        pc::GroupSample before{}, after{};
        before.nr = 2; after.nr = 3;
        pc::WindowDelta d;
        CHECK(!pc::window_delta(before, after, 2, &d), "nr mismatch delta rejected");
        CHECK(std::strcmp(d.reason, "nr-mismatch") == 0, "nr mismatch named");
    }

    if (failures) {
        std::fprintf(stderr, "perf_window_golden: %d FAILURES\n", failures);
        return 1;
    }
    std::printf("perf_window_golden: all decode scenarios pass\n");
    return 0;
}
