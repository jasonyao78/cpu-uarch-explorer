# SPDX-License-Identifier: Apache-2.0
add_executable(pmu_counter_smoke pmu_counter_smoke.cpp)
target_compile_options(pmu_counter_smoke PRIVATE -Wall -Wextra -Wpedantic)
