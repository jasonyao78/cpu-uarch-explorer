# SPDX-License-Identifier: Apache-2.0
# Platform-specific capability probes, scoped by backend id (the same
# values as the `backend` enum in runner/schema/record.schema.json).
# A subdir is added only when the build host matches that backend; this
# keeps e.g. mach-specific probes out of Linux/Android cross builds.
if(APPLE)
    add_subdirectory(macos-arm64)
endif()

if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    add_subdirectory(linux)
endif()

# Android arm64 currently consumes statically linked Linux UAPI probes produced
# by the linux-aarch64 cross preset; Android-specific APIs still belong in a
# separate backend directory when one is needed.
