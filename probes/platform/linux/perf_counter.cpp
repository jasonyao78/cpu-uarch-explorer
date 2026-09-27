// SPDX-License-Identifier: Apache-2.0

#include "perf_counter.h"

#include <cerrno>
#include <linux/perf_event.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <utility>

namespace cpu_uarch {
namespace {

int perf_event_open(perf_event_attr* attr, pid_t pid, int cpu) {
    return static_cast<int>(syscall(
        __NR_perf_event_open, attr, pid, cpu, -1, PERF_FLAG_FD_CLOEXEC));
}

void set_error(PerfCounterError* error, const char* stage, int error_number) {
    if (error == nullptr)
        return;
    error->stage = stage;
    error->error_number = error_number;
}

}  // namespace

PerfCounterSession::PerfCounterSession(std::vector<PerfEventSpec> specs) {
    entries_.reserve(specs.size());
    for (auto& spec : specs)
        entries_.push_back(Entry{std::move(spec), -1, {}});
}

PerfCounterSession::~PerfCounterSession() {
    disable_all();
    close_all();
}

bool PerfCounterSession::open_for_current_thread(PerfCounterError* error) {
    for (auto& entry : entries_) {
        perf_event_attr attr{};
        attr.type = entry.spec.type;
        attr.size = sizeof(attr);
        attr.config = entry.spec.config;
        attr.disabled = 1;
        attr.read_format = PERF_FORMAT_TOTAL_TIME_ENABLED
                         | PERF_FORMAT_TOTAL_TIME_RUNNING;
        entry.fd = perf_event_open(&attr, 0, -1);
        if (entry.fd < 0) {
            set_error(error, "perf-event-open", errno);
            close_all();
            return false;
        }
    }
    return true;
}

bool PerfCounterSession::start(PerfCounterError* error) {
    for (auto& entry : entries_) {
        if (ioctl(entry.fd, PERF_EVENT_IOC_RESET, 0) != 0) {
            set_error(error, "perf-reset", errno);
            disable_all();
            return false;
        }
    }
    for (auto& entry : entries_) {
        if (ioctl(entry.fd, PERF_EVENT_IOC_ENABLE, 0) != 0) {
            set_error(error, "perf-enable", errno);
            disable_all();
            return false;
        }
    }
    for (auto& entry : entries_) {
        if (!read_value(entry.fd, &entry.baseline, error, "read-initial")) {
            disable_all();
            return false;
        }
    }
    return true;
}

bool PerfCounterSession::stop(
        std::vector<PerfEventObservation>* observations,
        PerfCounterError* error) {
    std::vector<ReadValue> final_values(entries_.size());
    for (size_t index = 0; index < entries_.size(); ++index) {
        if (!read_value(entries_[index].fd, &final_values[index], error,
                        "read-final")) {
            disable_all();
            return false;
        }
    }
    if (!disable_all(error))
        return false;

    observations->clear();
    observations->reserve(entries_.size());
    for (size_t index = 0; index < entries_.size(); ++index) {
        const auto& entry = entries_[index];
        const auto& final = final_values[index];
        if (final.value < entry.baseline.value
                || final.time_enabled < entry.baseline.time_enabled
                || final.time_running < entry.baseline.time_running) {
            set_error(error, "counter-regressed", EOVERFLOW);
            observations->clear();
            return false;
        }
        const uint64_t time_enabled =
            final.time_enabled - entry.baseline.time_enabled;
        const uint64_t time_running =
            final.time_running - entry.baseline.time_running;
        if (time_running == 0 || time_running > time_enabled) {
            set_error(error, "counter-not-scheduled", EIO);
            observations->clear();
            return false;
        }
        observations->push_back(PerfEventObservation{
            entry.spec,
            final.value - entry.baseline.value,
            time_enabled,
            time_running,
        });
    }
    return true;
}

bool PerfCounterSession::read_value(int fd, ReadValue* value,
                                    PerfCounterError* error,
                                    const char* stage) {
    errno = 0;
    const ssize_t got = read(fd, value, sizeof(*value));
    if (got == static_cast<ssize_t>(sizeof(*value)))
        return true;
    set_error(error, stage, errno != 0 ? errno : EIO);
    return false;
}

bool PerfCounterSession::disable_all(PerfCounterError* error) {
    bool ok = true;
    for (auto& entry : entries_) {
        if (entry.fd >= 0 && ioctl(entry.fd, PERF_EVENT_IOC_DISABLE, 0) != 0) {
            if (ok)
                set_error(error, "perf-disable", errno);
            ok = false;
        }
    }
    return ok;
}

void PerfCounterSession::close_all() {
    for (auto& entry : entries_) {
        if (entry.fd >= 0) {
            close(entry.fd);
            entry.fd = -1;
        }
    }
}

bool perf_open_errno_is_unsupported(int error_number) {
    return error_number == EACCES || error_number == EPERM
        || error_number == ENOENT || error_number == ENODEV
        || error_number == EOPNOTSUPP || error_number == EINVAL;
}

}  // namespace cpu_uarch
