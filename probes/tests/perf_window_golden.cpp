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

    if (failures) {
        std::fprintf(stderr, "perf_window_golden: %d FAILURES\n", failures);
        return 1;
    }
    std::printf("perf_window_golden: all decode scenarios pass\n");
    return 0;
}
