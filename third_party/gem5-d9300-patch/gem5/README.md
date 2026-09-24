# gem5 Integration Assets

> 2026-09-24 迁入本仓（cpu-uarch-explorer）：路径从原项目的 `sim/gem5` /
> `thirdparty/gem5` 适配为 `third_party/gem5-d9300-patch/gem5` /
> `third_party/gem5`。原始 drop 只读归档于仓库外
> `../cpu-uarch-ref/gem5-d9300-patch/`（含 MANIFEST.sha256）。

- `configs/`, `src/`, `tests/`, `scripts/`, ...: local gem5 deltas kept in the
  same directory structure as upstream `third_party/gem5`
- `apply_patchset.sh`: sync helper that merges these mirrored directories into
  the gem5 submodule worktree for compilation

This directory is the authoritative home for all local gem5 deltas. The
`third_party/gem5` submodule should stay aligned with official upstream gem5,
and custom SoC work such as D9200/D9300 integration should be represented here
instead of being committed directly inside the submodule.

Workflow:

1. Update `third_party/gem5` by submodule.
2. Place any added or modified gem5 files under
   `third_party/gem5-d9300-patch/gem5/` using the same
   relative paths they have in upstream gem5.
   Top-level files such as `SConstruct` or `run_multicore.sh` can also be
   mirrored here when they are part of the local gem5 delta.
3. Run `apply_patchset.sh` to merge the delta into `third_party/gem5`.
4. Build from `third_party/gem5`.
