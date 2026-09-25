# SPDX-License-Identifier: Apache-2.0
# Linux aarch64 交叉编译工具链（GB10 接入任务 §3.3；也是 Android 接入的预演形态）。
# 构建宿主：Xeon（aarch64-linux-gnu-gcc 13 已装）；执行目标：GB10 / Android ARM64。
# 静态链接消除目标侧 glibc 版本依赖——定制 OS（DGX OS / Android）上唯一可靠的交付形态。
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_C_COMPILER aarch64-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER aarch64-linux-gnu-g++)
set(CMAKE_EXE_LINKER_FLAGS "-static" CACHE STRING
    "静态链接：GB10 接入任务书 §3.3（消除目标侧 glibc 依赖）")
# 交叉编译不能运行目标端二进制做编译器特性探测——按静态库探测
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)
