# SPDX-License-Identifier: Apache-2.0
# 共享探针支撑组件（M0-1）：页策略与 backing 审计（header-only INTERFACE）。
add_library(probe_common INTERFACE)
target_include_directories(probe_common INTERFACE ${CMAKE_CURRENT_SOURCE_DIR})
