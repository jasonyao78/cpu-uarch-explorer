// SPDX-License-Identifier: Apache-2.0
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace cpu_uarch {

struct PerfEventSpec {
    std::string label;
    uint32_t type;
    uint64_t config;
};

struct PerfEventObservation {
    PerfEventSpec spec;
    uint64_t count;
    uint64_t time_enabled_ns;
    uint64_t time_running_ns;
};

struct PerfCounterError {
    std::string stage;
    int error_number = 0;
};

// A small counting-only perf session for the current thread. Events are kept
// independent instead of grouped so this interface can later accept an uncore
// fd opened by a privilege-separated broker. start() records an immediate
// post-enable baseline; stop() reads before disable for downstream PMUs whose
// driver-side count is updated only while the event is not marked stopped.
class PerfCounterSession {
public:
    explicit PerfCounterSession(std::vector<PerfEventSpec> specs);
    ~PerfCounterSession();

    PerfCounterSession(const PerfCounterSession&) = delete;
    PerfCounterSession& operator=(const PerfCounterSession&) = delete;

    bool open_for_current_thread(PerfCounterError* error);
    bool start(PerfCounterError* error);
    bool stop(std::vector<PerfEventObservation>* observations,
              PerfCounterError* error);

private:
    struct ReadValue {
        uint64_t value = 0;
        uint64_t time_enabled = 0;
        uint64_t time_running = 0;
    };

    struct Entry {
        PerfEventSpec spec;
        int fd = -1;
        ReadValue baseline;
    };

    void close_all();
    bool disable_all(PerfCounterError* error = nullptr);
    static bool read_value(int fd, ReadValue* value, PerfCounterError* error,
                           const char* stage);

    std::vector<Entry> entries_;
};

bool perf_open_errno_is_unsupported(int error_number);

}  // namespace cpu_uarch
