#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run Linux PerfWindow class with synthetic syscall returns on macOS.

No PMU/target measurements. The production header is included unchanged;
minimal UAPI declarations and intercepted functions exercise control logic.
"""
from pathlib import Path
import argparse
import json
import subprocess
import tempfile

MOCK_UAPI = r'''
#pragma once
#include <cstdint>
struct perf_event_attr {
    uint32_t type, size;
    uint64_t config, read_format;
    uint64_t disabled:1, exclude_kernel:1, exclude_hv:1;
};
#define PERF_TYPE_RAW 4
#define PERF_FORMAT_TOTAL_TIME_ENABLED 1
#define PERF_FORMAT_TOTAL_TIME_RUNNING 2
#define PERF_FORMAT_GROUP 8
#define PERF_EVENT_IOC_ENABLE 0x2400
#define PERF_EVENT_IOC_DISABLE 0x2401
#define PERF_EVENT_IOC_SET_OUTPUT 0x2405
'''

HARNESS = r'''
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <type_traits>
#include <utility>
#include <cstdarg>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <linux/perf_event.h>
static size_t members = 0;
static bool fail_cycles = false;
static bool pad_to_capacity = false;
static bool zero_time = false;
static int read_mode = 0;
static std::vector<unsigned long> commands;
static std::vector<int> closed;
long review_open(long ignored, ...) {
    va_list ap; va_start(ap, ignored);
    auto *pe = va_arg(ap, perf_event_attr*);
    va_end(ap);
    if (fail_cycles && pe->config == 0x11) return -1;
    return 100 + (long)members++;
}
int review_ioctl(int, unsigned long command, ...) {
    commands.push_back(command); return 0;
}
ssize_t review_read(int, void *buffer, size_t capacity) {
    if (read_mode == 1) return -1;
    if (read_mode == 2) return 0;
    if (read_mode == 3) return 25;
    if (read_mode == 4) return 16;
    auto *words = static_cast<uint64_t*>(buffer);
    words[0] = (read_mode == 5) ? members+1 : members;
    words[1] = zero_time ? 0 : 1000;
    words[2] = zero_time ? 0 : 1000;
    for (size_t i=0;i<members;i++) words[3+i] = 111+i;
    if (read_mode == 6) return 24;
    return pad_to_capacity ? (ssize_t)capacity : (ssize_t)((3+members)*8);
}
int review_close(int fd) { closed.push_back(fd); return 0; }
// Standard platform headers are read first; only the included production
// header's Linux branch sees this macro. Syscalls use synthetic replacements.
#define __linux__ 1
#define SYS_perf_event_open 298
#define syscall review_open
#define ioctl review_ioctl
#define read review_read
#define close review_close
#include "perf_window.h"
#undef syscall
#undef ioctl
#undef read
#undef close
#undef __linux__
int main() {
    namespace pc=probe_common;
    pc::EventSpec specs[16];
    for(size_t i=0;i<16;i++) specs[i]={i+1,"event"};
    for (size_t n : {size_t(1),size_t(2),size_t(4),size_t(16)}) {
        members=0; commands.clear();
        pc::PerfWindow w;
        bool opened=w.open(specs,n); pc::GroupSample s;
        bool mask[16]={}; bool mux=true;
        std::printf("n=%zu actual_bytes=%zu opened=%d read_ok=%d\n",
            n,(3+n)*8,opened,w.review_read(&s,mask,&mux));
    }
    members=0; fail_cycles=true;
    pc::EventSpec failed_specs[]={{0x11,"cycles"},{0x05,"refill"},{0x34,"walk"}};
    pc::PerfWindow failed;
    failed.open(failed_specs,3);
    for (size_t i=0;i<3;i++) {
        try { std::printf("spec=%zu failed=%d value_index=%d name=%s\n",i,
                  failed.failed(i),failed.value_index(i),failed.name(i).c_str()); }
        catch (const std::exception&) { std::printf("spec=%zu name=out_of_range\n",i); }
    }
    members=0; fail_cycles=false; zero_time=true; pad_to_capacity=false;
    pc::PerfWindow zero; zero.open(specs,16);
    pc::GroupSample s; bool mask[16]={}; bool mux=true;
    bool accepted=zero.review_read(&s,mask,&mux);
    std::printf("synthetic_zero_time read_ok=%d mux=%d enabled=%llu running=%llu\n",
        accepted,mux,(unsigned long long)s.time_enabled,(unsigned long long)s.time_running);
    members=0;
    static_assert(!std::is_copy_constructible<pc::PerfWindow>::value);
    static_assert(!std::is_copy_assignable<pc::PerfWindow>::value);
    static_assert(std::is_move_constructible<pc::PerfWindow>::value);
    pc::PerfWindow owner;
    owner.open(specs,1);
    pc::PerfWindow moved(std::move(owner));
    pc::PerfWindow target;
    target.open(specs,1);
    closed.clear();
    target = std::move(moved);
    moved.close_all(); owner.close_all(); target.close_all();
    std::printf("move_transfer_close_calls=%zu fds=%d,%d\n",closed.size(),closed.at(0),closed.at(1));
    members=0; zero_time=false;
    pc::PerfWindow malformed;
    malformed.open(specs,2);
    for (int mode : {1,2,3,4,5,6}) {
        read_mode=mode;
        bool accepted=malformed.review_read(&s,mask,&mux);
        std::printf("malformed_mode=%d read_ok=%d reason=%s\n",mode,accepted,malformed.last_error());
    }

}
'''


def main():
    """Compile/run a mock harness; completion reports diagnostics, not a pass."""
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-tree',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='m0b-perf-review-') as temporary:
        temp=Path(temporary)
        (temp/'linux').mkdir()
        (temp/'linux/perf_event.h').write_text(MOCK_UAPI)
        (temp/'harness.cpp').write_text(HARNESS)
        command=['clang++','-std=c++17','-O0','-I',str(temp),'-I',str(args.source_tree/'probes/common'),
                 str(temp/'harness.cpp'),'-o',str(temp/'harness')]
        compiled=subprocess.run(command,capture_output=True,text=True)
        if compiled.returncode:
            raise RuntimeError(compiled.stderr)
        result=subprocess.run([str(temp/'harness')],capture_output=True,text=True,check=True)
        args.out.write_text(json.dumps({'evidence':'synthetic syscall injection, no kernel/PMU execution',
                                      'compile_stderr':compiled.stderr,'output':result.stdout},indent=2)+'\n')
        print(result.stdout,end='')


if __name__=='__main__':
    main()
