# SPDX-License-Identifier: Apache-2.0
# Platform-specific capability probes, scoped by backend id (the same
# values as the `backend` enum in runner/schema/record.schema.json).
# A subdir is added only when the build host matches that backend; this
# keeps e.g. mach-specific probes out of Linux/Android cross builds.
if(APPLE)
    add_subdirectory(macos-arm64)
endif()
# future: if(CMAKE_SYSTEM_NAME STREQUAL "Linux") add_subdirectory(linux-x86_64) ...
# future: android-arm64 probes are built with the NDK toolchain file instead.
