# Runbook：在 Xeon 服务器上构建 gem5（D9300 overlay）

> 前置约定（v0.3 §2.2）：代码与构建目录放 **NVMe**（2TB Samsung 990 PRO），不要放 HDD 的 `/hdd_10T/...` 工作目录。gem5 全量构建约 20–40 分钟（56C + NVMe）。

## 0. 获取代码（二选一）

**方式 A：GitHub 克隆（推荐，私有仓需认证）**

```bash
# 服务器上先完成 gh 认证（jasonyao78 账号）：
#   gh auth login
gh repo clone jasonyao78/cpu-uarch-explorer -- --recurse-submodules
cd cpu-uarch-explorer
# 若已克隆但未带子模块：
#   git submodule update --init
```

**方式 B：rsync 本机直传（服务器无法访问 GitHub 时用）**

```bash
# 在 M4 Pro 本机执行。注意：
# 1. macOS 自带 openrsync（2.6.9 兼容）不支持 --info=progress2，用 --progress；
#    想要总进度条可 brew install rsync 后用 rsync3 的 --info=progress2。
# 2. 必须排除构建产物（构建目录已收敛为单一 build/ 树，ADR-0008；
#    rsync 的 'build/' 模式按目录名匹配任意层级，一条规则全覆盖）。
# 3. 目标路径放 NVMe（先 lsblk / findmnt 确认挂载点；home 目录可能在 HDD 上）。
rsync -a --progress \
  --exclude '.DS_Store' \
  --exclude 'build/' \
  /Users/michaelyao/workspace/cpu-uarch-explorer/ \
  <server>:/path/on/nvme/cpu-uarch-explorer/
# submodule 说明：absorbgitdirs 后 third_party/gem5/.git 是指向
# ../../.git/modules/third_party/gem5 的相对指针，rsync -a 带上 .git 即在服务器侧可用。
```

## 1. Python 环境（uv，ADR-0007）

```bash
# uv 管本仓 runner/analysis 依赖；gem5 构建用系统工具链（§3，勿混用！）
cd /path/on/nvme/cpu-uarch-explorer
uv sync        # 按 uv.lock 建 .venv（uv 托管 CPython 3.12 + scons + protobuf）
```

> ⚠️ **教训（2026-09-24）**：不要把 uv 托管 Python 的 bin 前置到 PATH 去驱动 gem5 构建，
> 也不要在 `third_party/gem5` 目录内执行 `uv run`（gem5 自带 pyproject.toml 会让 uv 另建 venv）。
> 两者都会让 gem5py（内嵌 Python 的代码生成器）落到 python-build-standalone 的非标准布局上，
> 导致 codegen 崩溃（Error 134 / `No module named '_contextvars'`）。
> gem5 构建用系统 scons（§3）；gem5 运行时如需 protobuf：`sudo apt install python3-protobuf`。

## 1b. 系统依赖（Ubuntu 24.04，已具备）

`build-essential`（gcc/g++/make/elf.h）、`protobuf-compiler`（protoc 3.21）、`python3-dev` 已在系统内；scons/protobuf 的 Python 侧由 uv 提供，**无需 apt/pip 混合安装**。tcmalloc / capstone / png 为可选增强，缺失只产生警告。

## 1c. 旧方式存档（勿用）

conda Python（gem5 链接检查失败）；系统 pip 直装（PEP 668 漂移）。详见 ADR-0007。

## 2. 同步 D9300 overlay

```bash
sh third_party/gem5-d9300-patch/gem5/apply_patchset.sh
```

## 3. 构建

```bash
cd third_party/gem5
scons build/ARM/gem5.opt -j56 2>&1 | tee build-xeon-arm64.log
```

用系统 scons（`/usr/bin/scons`，apt 自带）+ 系统 python3.12——gem5 CI 参考环境；不要在此目录用 `uv run`（原因见 §1 ⚠️）。

## 4. 验证与回传

```bash
./build/ARM/gem5.opt --version
tail -5 build-xeon-arm64.log
```

把 **scons 退出码** 和日志尾部贴回 OI-1（Issue #1），并注明构建目录所在磁盘（NVMe/HDD）。

## 附：macOS 构建结论（2026-09-24 实测，勿重复踩坑）

configure 通过，922 个对象编译成功（含 delta 的 `coral_backend` / `coral_stagea_backend` / `npu_device`），唯一硬错误：

```
src/dev/npu/coral_verilated_backend.cc: fatal error: 'elf.h' file not found
```

`<elf.h>` 是 glibc 专属头文件，macOS（Mach-O）不提供。verilated NPU 后端本身就是 Linux + Verilator + NPU RTL 流程，**macOS 不做 gem5 构建平台**。若将来需要 macOS 本地构建非 verilated 变体，可在 delta 中对 verilated 后端加 `__APPLE__` 守卫（backlog，需 NPU 流程负责人确认）。

## 附2：Linux 构建失败记录 #2（2026-09-24，已解决）

**现象**：`uv run scons`（或 PATH 前置 uv 托管 Python）驱动构建时，codegen 阶段批量崩溃：

```
terminate called after throwing an instance of 'pybind11::error_already_set'
  what():  ModuleNotFoundError: No module named '_contextvars'
scons: *** [build/ARM/params/PartitionManager.hh] Error 134
```

**根因**：uv 托管 Python（python-build-standalone）的 `lib-dynload/` 只有 3 个 `.so`（其余扩展模块静态链入 libpython）。gem5 的 gem5py（内嵌 Python 的代码生成器）按 uv 的 `python3-config` 链接/解析后，其内嵌解释器的模块解析在该非标准布局下断裂。与 delta 无关（同 overlay 用系统 scons 即通过）。

**解决**：系统 scons 构建（gem5py 按系统 python3-config 链接，全链路一致）。**验证：2026-09-24 系统 scons 构建成功（`build/ARM/gem5.opt` 954MB）。** 另注意：在 `third_party/gem5` 内执行 `uv run` 会因 gem5 自带 `pyproject.toml` 另建 venv，同样会污染构建环境，一并禁止。

## 附3：冒烟验证（2026-09-24 通过）

```bash
# 编译 ARM64 静态测试程序（服务器已有交叉编译器 /usr/bin/aarch64-linux-gnu-gcc）
printf "int main(void){return 42;}\n" > /tmp/h.c
aarch64-linux-gnu-gcc -static -O1 -o /tmp/hello-arm64 /tmp/h.c
# 运行 SE 仿真（ARM-only 构建跑 x86 二进制会报 "No SE workload is compatible"，属预期）
cd third_party/gem5
./build/ARM/gem5.opt configs/deprecated/example/se.py --cmd /tmp/hello-arm64
# 预期：Exiting @ tick <N> because exiting with last active thread context，退出码 0
```

## 附4：增量树最小集回归验证（2026-09-25 已完成，留存作流程参考）

修剪 + 改钉后的最终状态为 **v25.0.0.1 + 134 文件有意 delta**。验证当日踩过三个坑，均为增量树缺陷而非流程问题（m5.internal 引用、IQUnit 结构冲突、CheckerCPU 注销链，详见 intake 文档）。最终生效的流程：

```bash
cd ~/cpu-uarch-explorer                     # Xeon 服务器（真实地址见 data/private/hosts.md）
git pull && git submodule update --init     # 确认 gem5 在 ddd4ae35ad（v25.0.0.1）

# 1. submodule 重置纯净（apply_patchset 只拷不删，旧残留不会自己消失）
git -C third_party/gem5 checkout -- .
git -C third_party/gem5 clean -fd
git -C third_party/gem5 status --short | wc -l    # 预期 0

# 2. 同步 overlay（基线断言 + 脏树检测会自动把关）
sh third_party/gem5-d9300-patch/gem5/apply_patchset.sh
git -C third_party/gem5 status --short | wc -l    # 预期 ≈53（26 改 + 目录折叠的新增）

# 3. 干净重建（基线切换后 build/ARM 必须删掉重来，陈旧 codegen 会报 phantom 错误）
cd third_party/gem5
rm -rf build/ARM
scons build/ARM/gem5.opt -j56 2>&1 | tee build-xeon-arm64.log

# 4. 冒烟（注意：gem5 没有 --version 选项，勿加）
./build/ARM/gem5.opt configs/deprecated/example/se.py --cmd /tmp/hello-arm64
```

**2026-09-25 验证结果**：gem5.opt 910M、0 error；冒烟 `Exiting @ tick 46213000`，退出码 0。

**rsync 教训**：从本机同步仓库到服务器时**必须带 `--delete`**（至少对 `third_party/gem5-d9300-patch/`），否则本机删除的文件在服务器上残留，overlay 会同步出陈旧内容（当日因此复现了一次已修复的 CheckerCPU 错误）。`--delete` 配合 `--exclude 'build/'` 使用是安全的（build 被排除在删除集合外）。

**回报内容**：scons 退出码、`build-xeon-arm64.log` 尾部 30 行、第 2 步的文件数，贴回 OI-1。

**失败回滚**（保底路径）：

```bash
cd /path/on/nvme/cpu-uarch-explorer
git checkout <修剪前 commit> -- third_party/gem5-d9300-patch
git -C third_party/gem5 checkout -- . && git -C third_party/gem5 clean -fd
sh third_party/gem5-d9300-patch/gem5/apply_patchset.sh
cd third_party/gem5 && scons build/ARM/gem5.opt -j56
```

**失败的第一嫌疑**：保留的 7 个 pybind11 新增文件与 v25.1 的 pybind11 树冲突，或 27 个 O3/内存改动文件与 v25.1 API 不兼容——前者直接删这 7 个文件重试；后者走 port 路线（见 intake 文档末节）。
