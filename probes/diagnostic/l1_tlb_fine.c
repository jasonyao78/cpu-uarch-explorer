/* SPDX-License-Identifier: Apache-2.0
 * New v2 finite grid only; implementation reused without changing old raw.
 * docs/design/2026-10-13-l1-tlb-fine.md.
 */
#define CPU_UARCH_L1_D_GRID 32,94,95,96,97,98,99,100,104
#define CPU_UARCH_L1_I_GRID 32,46,47,48,49,50,51,52,56
#define CPU_UARCH_L1_VERSION 2
#include "l1_tlb_reach.c"
