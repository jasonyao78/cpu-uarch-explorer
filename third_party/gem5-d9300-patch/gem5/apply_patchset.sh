#!/bin/sh

set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
# default target: the gem5 submodule checkout at third_party/gem5
# (SCRIPT_DIR is third_party/gem5-d9300-patch/gem5, so ../../gem5)
GEM5_REPO="${GEM5_REPO:-${SCRIPT_DIR}/../../gem5}"

if ! git -C "${GEM5_REPO}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "error: gem5 submodule not found: ${GEM5_REPO}" >&2
    exit 1
fi

# 基线断言（2026-09-25，OI-1 教训）：增量树基于 v25.0.0.1 开发，
# 同步到错误的基线会产生"静默版本混合"（曾致 m5.internal / IQUnit 类
# 引用失效）。钉错基线时拒绝同步；确需跳过用 GEM5_SKIP_BASELINE_CHECK=1。
EXPECTED_BASELINE="v25.0.0.1"
if [ "${GEM5_SKIP_BASELINE_CHECK:-0}" != "1" ]; then
    # 比较 commit 哈希而非 tag 名：annotated tag 的 describe 输出格式不稳定
    expected_commit="$(git -C "${GEM5_REPO}" rev-parse "${EXPECTED_BASELINE}^{commit}" 2>/dev/null || true)"
    actual_commit="$(git -C "${GEM5_REPO}" rev-parse HEAD)"
    if [ -z "${expected_commit}" ] || [ "${actual_commit}" != "${expected_commit}" ]; then
        echo "error: gem5 baseline mismatch: expect ${EXPECTED_BASELINE} (${expected_commit:-tag-missing})," \
             "got $(git -C "${GEM5_REPO}" rev-parse --short HEAD)" >&2
        echo "hint: git -C ${GEM5_REPO} checkout ${EXPECTED_BASELINE}，" \
             "或确认移植完成后用 GEM5_SKIP_BASELINE_CHECK=1 跳过" >&2
        exit 1
    fi
fi

# 预存脏树检测：同步前工作树必须纯净，否则旧增量残留会与新增量混合
# （apply_patchset 只拷不删；build/ 等 gitignore 内容不受影响）。
if [ -n "$(git -C "${GEM5_REPO}" status --porcelain --untracked-files=normal)" ]; then
    echo "error: gem5 worktree is dirty; reset first:" >&2
    echo "  git -C ${GEM5_REPO} checkout -- . && git -C ${GEM5_REPO} clean -fd" >&2
    exit 1
fi

has_delta=0
for path in configs src ext include system util tests scripts; do
    if [ -e "${SCRIPT_DIR}/${path}" ]; then
        has_delta=1
        break
    fi
done

for file in SConstruct requirements.txt run_multicore.sh; do
    if [ -e "${SCRIPT_DIR}/${file}" ]; then
        has_delta=1
        break
    fi
done

if [ "${has_delta}" -ne 1 ]; then
    echo "error: no mirrored gem5 delta directories found under ${SCRIPT_DIR}" >&2
    exit 1
fi

copy_if_changed()
{
    source_path="$1"
    destination_path="$2"
    if [ ! -f "${destination_path}" ] ||
       [ "${source_path}" -nt "${destination_path}" ] ||
       ! cmp -s "${source_path}" "${destination_path}"; then
        mkdir -p "$(dirname "${destination_path}")"
        cp "${source_path}" "${destination_path}"
        # SCons must see overlay updates as newer than existing objects.
        touch "${destination_path}"
    fi
}

sync_tree()
{
    source_root="$1"
    destination_root="$2"
    (cd "${source_root}" && find . -type d -print) |
        while IFS= read -r relative_path; do
            mkdir -p "${destination_root}/${relative_path}"
        done
    (cd "${source_root}" && find . -type f -print) |
        while IFS= read -r relative_path; do
            copy_if_changed "${source_root}/${relative_path}" \
                "${destination_root}/${relative_path}"
        done
}

echo "[gem5-patchset] syncing mirrored directories into ${GEM5_REPO}"
for path in configs src ext include system util tests scripts; do
    if [ -e "${SCRIPT_DIR}/${path}" ]; then
        sync_tree "${SCRIPT_DIR}/${path}" "${GEM5_REPO}/${path}"
    fi
done

for file in SConstruct requirements.txt run_multicore.sh; do
    if [ -e "${SCRIPT_DIR}/${file}" ]; then
        copy_if_changed "${SCRIPT_DIR}/${file}" "${GEM5_REPO}/${file}"
    fi
done

echo "[gem5-patchset] done"
