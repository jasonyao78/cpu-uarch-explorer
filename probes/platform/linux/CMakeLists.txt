# SPDX-License-Identifier: Apache-2.0
add_library(linux_perf_counter STATIC perf_counter.cpp)
target_include_directories(linux_perf_counter PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_options(linux_perf_counter PRIVATE -Wall -Wextra -Wpedantic)
target_compile_definitions(linux_perf_counter INTERFACE CPU_UARCH_HAVE_LINUX_PERF=1)

add_executable(pmu_counter_smoke pmu_counter_smoke.cpp)
target_compile_options(pmu_counter_smoke PRIVATE -Wall -Wextra -Wpedantic)
