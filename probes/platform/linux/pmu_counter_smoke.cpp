// SPDX-License-Identifier: Apache-2.0
// Linux perf counting-event smoke probe.
//
// This is deliberately a capability probe, not a cache-geometry benchmark.
// It validates that one PMU/config can be opened, enabled, read, and made to
// observe either an idle interval or a bounded streaming-read workload. The
// PMU type may be resolved from a safe sysfs name or supplied explicitly when
// sysfs discovery is outside the caller's privilege boundary. Qualcomm's
// downstream LLCC driver keeps a driver-side cumulative
// total, so PERF_EVENT_IOC_RESET cannot be assumed to make the next read zero:
// the reported observation is always final - an immediate post-enable
// baseline. The final read is deliberately issued while the event is still
// enabled: some downstream drivers update event->count only while their
// private hw state is not STOPPED. The raw endpoints are emitted for audit.

#include <cerrno>
#include <climits>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <getopt.h>
#include <limits>
#include <linux/perf_event.h>
#include <sched.h>
#include <string>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

namespace {

constexpr uint64_t kMaxDurationMs = 10 * 60 * 1000;
constexpr uint64_t kMaxBufferMiB = 4096;
constexpr size_t kCacheLineBytes = 64;

struct Options {
    std::string pmu;
    uint32_t type = 0;
    bool type_set = false;
    uint64_t config = 0;
    bool config_set = false;
    std::string scope;
    int cpu = -1;
    bool cpu_set = false;
    std::string workload;
    uint64_t duration_ms = 0;
    uint64_t buffer_mib = 0;
};

struct ReadValue {
    uint64_t value;
    uint64_t time_enabled;
    uint64_t time_running;
};

volatile uint64_t g_sink = 0;

void usage(const char* program) {
    std::fprintf(
        stderr,
        "usage: %s (--pmu NAME | --type N) --config N "
        "--scope cpu|thread [--cpu N] "
        "--workload idle|stream-read --duration-ms N --buffer-mib N\n",
        program);
}

[[noreturn]] void die_usage(const char* program, const char* message) {
    std::fprintf(stderr, "error: %s\n", message);
    usage(program);
    std::exit(1);
}

bool safe_pmu_name(const std::string& name) {
    if (name.empty() || name == "." || name == "..")
        return false;
    for (unsigned char ch : name) {
        const bool valid = (ch >= 'a' && ch <= 'z')
                        || (ch >= 'A' && ch <= 'Z')
                        || (ch >= '0' && ch <= '9')
                        || ch == '_' || ch == '-' || ch == '.';
        if (!valid)
            return false;
    }
    return true;
}

bool parse_u64(const char* text, uint64_t* value) {
    if (text == nullptr || text[0] == '\0' || text[0] == '-')
        return false;
    errno = 0;
    char* end = nullptr;
    const unsigned long long parsed = std::strtoull(text, &end, 0);
    if (errno != 0 || end == text || *end != '\0')
        return false;
    *value = static_cast<uint64_t>(parsed);
    return true;
}

bool parse_cpu(const char* text, int* cpu) {
    uint64_t parsed = 0;
    if (!parse_u64(text, &parsed) || parsed > static_cast<uint64_t>(INT_MAX))
        return false;
    *cpu = static_cast<int>(parsed);
    return true;
}

Options parse_options(int argc, char** argv) {
    Options options;
    enum : int {
        kPmu = 1000,
        kType,
        kConfig,
        kScope,
        kCpu,
        kWorkload,
        kDurationMs,
        kBufferMiB,
    };
    const option long_options[] = {
        {"pmu", required_argument, nullptr, kPmu},
        {"type", required_argument, nullptr, kType},
        {"config", required_argument, nullptr, kConfig},
        {"scope", required_argument, nullptr, kScope},
        {"cpu", required_argument, nullptr, kCpu},
        {"workload", required_argument, nullptr, kWorkload},
        {"duration-ms", required_argument, nullptr, kDurationMs},
        {"buffer-mib", required_argument, nullptr, kBufferMiB},
        {nullptr, 0, nullptr, 0},
    };

    while (true) {
        const int parsed = getopt_long(argc, argv, "", long_options, nullptr);
        if (parsed == -1)
            break;
        switch (parsed) {
        case kPmu:
            options.pmu = optarg;
            break;
        case kType: {
            uint64_t parsed_type = 0;
            if (!parse_u64(optarg, &parsed_type)
                    || parsed_type > std::numeric_limits<uint32_t>::max())
                die_usage(argv[0], "type must be a 32-bit unsigned integer");
            options.type = static_cast<uint32_t>(parsed_type);
            options.type_set = true;
            break;
        }
        case kConfig:
            if (!parse_u64(optarg, &options.config))
                die_usage(argv[0], "config must be a base-0 unsigned integer");
            options.config_set = true;
            break;
        case kScope:
            options.scope = optarg;
            break;
        case kCpu:
            if (!parse_cpu(optarg, &options.cpu))
                die_usage(argv[0], "cpu must be a non-negative integer");
            options.cpu_set = true;
            break;
        case kWorkload:
            options.workload = optarg;
            break;
        case kDurationMs:
            if (!parse_u64(optarg, &options.duration_ms))
                die_usage(argv[0], "duration-ms must be an unsigned integer");
            break;
        case kBufferMiB:
            if (!parse_u64(optarg, &options.buffer_mib))
                die_usage(argv[0], "buffer-mib must be an unsigned integer");
            break;
        default:
            usage(argv[0]);
            std::exit(1);
        }
    }

    if (optind != argc)
        die_usage(argv[0], "unexpected positional argument");
    const bool pmu_set = !options.pmu.empty();
    if (pmu_set == options.type_set)
        die_usage(argv[0], "exactly one of --pmu or --type is required");
    if (pmu_set && !safe_pmu_name(options.pmu))
        die_usage(argv[0], "pmu must contain only letters, digits, '.', '_' or '-'");
    if (!options.config_set)
        die_usage(argv[0], "--config is required");
    if (options.scope != "cpu" && options.scope != "thread")
        die_usage(argv[0], "scope must be cpu or thread");
    if (options.scope == "cpu" && !options.cpu_set)
        die_usage(argv[0], "cpu scope requires --cpu");
    if (options.workload != "idle" && options.workload != "stream-read")
        die_usage(argv[0], "workload must be idle or stream-read");
    if (options.duration_ms == 0 || options.duration_ms > kMaxDurationMs)
        die_usage(argv[0], "duration-ms must be in 1..600000");
    if (options.buffer_mib == 0 || options.buffer_mib > kMaxBufferMiB)
        die_usage(argv[0], "buffer-mib must be in 1..4096");
    return options;
}

int unsupported(const char* stage, int error_number) {
    std::fprintf(stderr, "unsupported: stage=%s errno=%d error=%s\n",
                 stage, error_number, std::strerror(error_number));
    return 2;
}

int runtime_error(const char* stage, int error_number) {
    std::fprintf(stderr, "error: stage=%s errno=%d error=%s\n",
                 stage, error_number, std::strerror(error_number));
    return 1;
}

bool unsupported_open_errno(int error_number) {
    return error_number == EACCES || error_number == EPERM
        || error_number == ENOENT || error_number == ENODEV
        || error_number == EOPNOTSUPP || error_number == EINVAL;
}

bool read_pmu_type(const std::string& pmu, uint32_t* type, int* error_number) {
    const std::string path = "/sys/bus/event_source/devices/" + pmu + "/type";
    std::ifstream input(path);
    if (!input) {
        *error_number = errno != 0 ? errno : ENOENT;
        return false;
    }
    unsigned long long parsed = 0;
    input >> parsed;
    input >> std::ws;
    if (!input.eof() || parsed > std::numeric_limits<uint32_t>::max()) {
        *error_number = EINVAL;
        return false;
    }
    *type = static_cast<uint32_t>(parsed);
    return true;
}

bool pin_to_cpu(int cpu) {
    if (cpu < 0 || cpu >= CPU_SETSIZE) {
        errno = EINVAL;
        return false;
    }
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    return sched_setaffinity(0, sizeof(set), &set) == 0;
}

int perf_event_open(perf_event_attr* attr, pid_t pid, int cpu) {
    return static_cast<int>(syscall(
        __NR_perf_event_open, attr, pid, cpu, -1, PERF_FLAG_FD_CLOEXEC));
}

bool read_counter(int fd, ReadValue* value) {
    const ssize_t got = read(fd, value, sizeof(*value));
    return got == static_cast<ssize_t>(sizeof(*value));
}

uint64_t monotonic_ns() {
    timespec value{};
    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0)
        return 0;
    return static_cast<uint64_t>(value.tv_sec) * 1000000000ULL
         + static_cast<uint64_t>(value.tv_nsec);
}

bool idle_until(uint64_t duration_ns) {
    timespec request{
        static_cast<time_t>(duration_ns / 1000000000ULL),
        static_cast<long>(duration_ns % 1000000000ULL),
    };
    while (nanosleep(&request, &request) != 0) {
        if (errno != EINTR)
            return false;
    }
    return true;
}

bool stream_read_until(const uint8_t* buffer, size_t bytes, uint64_t duration_ns,
                       uint64_t* bytes_read) {
    const uint64_t start = monotonic_ns();
    if (start == 0)
        return false;
    const uint64_t deadline = start + duration_ns;
    uint64_t total = 0;
    uint64_t sum = 0;
    do {
        for (size_t offset = 0; offset + sizeof(uint64_t) <= bytes;
             offset += kCacheLineBytes) {
            uint64_t value = 0;
            std::memcpy(&value, buffer + offset, sizeof(value));
            sum += value;
            if (total > std::numeric_limits<uint64_t>::max() - sizeof(value)) {
                errno = EOVERFLOW;
                return false;
            }
            total += sizeof(value);
        }
    } while (monotonic_ns() < deadline);
    g_sink = sum;
    *bytes_read = total;
    return true;
}

}  // namespace

int main(int argc, char** argv) {
    const Options options = parse_options(argc, argv);
    if (options.cpu_set && !pin_to_cpu(options.cpu))
        return runtime_error("sched_setaffinity", errno);

    uint32_t pmu_type = options.type;
    if (!options.type_set) {
        int type_error = 0;
        if (!read_pmu_type(options.pmu, &pmu_type, &type_error))
            return unsupported("read-pmu-type", type_error);
    }

    const uint64_t mib = 1024ULL * 1024ULL;
    if (options.buffer_mib > std::numeric_limits<size_t>::max() / mib)
        return runtime_error("buffer-size-overflow", EOVERFLOW);
    const size_t buffer_bytes = static_cast<size_t>(options.buffer_mib * mib);
    void* mapping = mmap(nullptr, buffer_bytes, PROT_READ | PROT_WRITE,
                         MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (mapping == MAP_FAILED)
        return runtime_error("mmap", errno);
    auto* buffer = static_cast<uint8_t*>(mapping);
    for (size_t offset = 0; offset < buffer_bytes; offset += kCacheLineBytes)
        buffer[offset] = static_cast<uint8_t>((offset / kCacheLineBytes) | 1U);

    perf_event_attr attr{};
    attr.type = pmu_type;
    attr.size = sizeof(attr);
    attr.config = options.config;
    attr.disabled = 1;
    attr.read_format = PERF_FORMAT_TOTAL_TIME_ENABLED
                     | PERF_FORMAT_TOTAL_TIME_RUNNING;

    const pid_t pid = options.scope == "cpu" ? -1 : 0;
    const int event_cpu = options.scope == "cpu"
        ? options.cpu : (options.cpu_set ? options.cpu : -1);
    const int fd = perf_event_open(&attr, pid, event_cpu);
    if (fd < 0) {
        const int saved = errno;
        munmap(mapping, buffer_bytes);
        return unsupported_open_errno(saved)
            ? unsupported("perf-event-open", saved)
            : runtime_error("perf-event-open", saved);
    }

    if (ioctl(fd, PERF_EVENT_IOC_RESET, 0) != 0) {
        const int saved = errno;
        close(fd);
        munmap(mapping, buffer_bytes);
        return runtime_error("perf-reset", saved);
    }
    if (ioctl(fd, PERF_EVENT_IOC_ENABLE, 0) != 0) {
        const int saved = errno;
        close(fd);
        munmap(mapping, buffer_bytes);
        return runtime_error("perf-enable", saved);
    }

    ReadValue initial{};
    if (!read_counter(fd, &initial)) {
        const int saved = errno != 0 ? errno : EIO;
        ioctl(fd, PERF_EVENT_IOC_DISABLE, 0);
        close(fd);
        munmap(mapping, buffer_bytes);
        return runtime_error("read-initial", saved);
    }

    const uint64_t duration_ns = options.duration_ms * 1000000ULL;
    uint64_t bytes_read = 0;
    const bool workload_ok = options.workload == "idle"
        ? idle_until(duration_ns)
        : stream_read_until(buffer, buffer_bytes, duration_ns, &bytes_read);
    if (!workload_ok) {
        const int saved = errno != 0 ? errno : EIO;
        ioctl(fd, PERF_EVENT_IOC_DISABLE, 0);
        close(fd);
        munmap(mapping, buffer_bytes);
        return runtime_error("workload", saved);
    }

    ReadValue final{};
    if (!read_counter(fd, &final)) {
        const int saved = errno != 0 ? errno : EIO;
        ioctl(fd, PERF_EVENT_IOC_DISABLE, 0);
        close(fd);
        munmap(mapping, buffer_bytes);
        return runtime_error("read-final", saved);
    }
    if (ioctl(fd, PERF_EVENT_IOC_DISABLE, 0) != 0) {
        const int saved = errno;
        close(fd);
        munmap(mapping, buffer_bytes);
        return runtime_error("perf-disable", saved);
    }
    close(fd);
    munmap(mapping, buffer_bytes);

    if (final.value < initial.value
            || final.time_enabled < initial.time_enabled
            || final.time_running < initial.time_running)
        return runtime_error("counter-regressed", EOVERFLOW);

    const uint64_t count_delta = final.value - initial.value;
    const uint64_t time_enabled = final.time_enabled - initial.time_enabled;
    const uint64_t time_running = final.time_running - initial.time_running;
    std::printf(
        "status=ok pmu=%s type_source=%s type=%u config=%llu "
        "scope=%s cpu=%d workload=%s "
        "count_initial=%llu count_final=%llu count_delta=%llu "
        "time_enabled_ns=%llu time_running_ns=%llu bytes_read=%llu "
        "buffer_mib=%llu duration_ms=%llu\n",
        options.type_set ? "explicit" : options.pmu.c_str(),
        options.type_set ? "explicit" : "sysfs", pmu_type,
        static_cast<unsigned long long>(options.config), options.scope.c_str(),
        options.cpu_set ? options.cpu : -1, options.workload.c_str(),
        static_cast<unsigned long long>(initial.value),
        static_cast<unsigned long long>(final.value),
        static_cast<unsigned long long>(count_delta),
        static_cast<unsigned long long>(time_enabled),
        static_cast<unsigned long long>(time_running),
        static_cast<unsigned long long>(bytes_read),
        static_cast<unsigned long long>(options.buffer_mib),
        static_cast<unsigned long long>(options.duration_ms));
    return 0;
}
