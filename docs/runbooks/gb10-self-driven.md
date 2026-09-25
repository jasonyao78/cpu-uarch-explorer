# Runbook：GB10（DGX Spark）自驱模式——下行构建、能力发现、首跑、物理回传

> 依据：`docs/tasks/2026-09-25-gb10-platform-onboarding.md`（自驱模式修订版）。
> 网络事实：Mac↔GB10 **无 SSH**；GB10 可 `git clone/pull` GitHub（私有仓需 `gh auth login`，只读下行）；上行只能物理介质（USB-C）。
> 数据纪律：GB10 侧**不 commit/push**（提交统一 Mac 收口）；run 的 raw/ 保留 GB10 本地备查，不回传。

## 0. 一次性准备（GB10 侧）

```bash
gh auth login          # 登录能读私有仓 jasonyao78/cpu-uarch-explorer 的账号
git clone https://github.com/jasonyao78/cpu-uarch-explorer.git
cd cpu-uarch-explorer
uv sync                # runner/analysis 依赖（.python-version 钉 3.12）
cmake --preset linux-aarch64-release && cmake --build --preset linux-aarch64-release
```

工具缺失时按 DGX OS 常规方式安装（`sudo apt install cmake g++`；uv 见 astral.sh）。**不做任何需要 sudo 的测量前置**（本期不锁频、不分配 hugepage——只读探测）。

## 1. 能力发现（GB10 上执行，输出全部贴回给 Mac 侧代理）

```bash
echo '=== lscpu ==='; lscpu | grep -E '^CPU\(s\)|Model name|Thread|Core|Socket|L1d|L1i|L2|L3|MHz|Hypervisor'
echo '=== topology cpu0/cpu5/cpu10/cpu15 ==='
for c in 0 5 10 15; do echo "-- cpu$c: core_id=$(cat /sys/devices/system/cpu/cpu$c/topology/core_id) cluster=$(cat /sys/devices/system/cpu/cpu$c/topology/cluster_id 2>/dev/null || echo NA) die=$(cat /sys/devices/system/cpu/cpu$c/topology/die_id 2>/dev/null || echo NA)"; done
echo '=== cache cpu0 ==='
for i in /sys/devices/system/cpu/cpu0/cache/index*; do echo "$(basename $i): L$(cat $i/level) $(cat $i/type) $(cat $i/size) ways=$(cat $i/ways_of_associativity 2>/dev/null) shared=$(cat $i/shared_cpu_list)"; done
echo '=== cpufreq ==='
ls /sys/devices/system/cpu/cpu0/cpufreq/ 2>/dev/null && cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null || echo 'no cpufreq sysfs'
echo '=== hugepage ==='; cat /proc/sys/vm/nr_hugepages
echo '=== timer ==='; python3 -c "import os; print('MONOTONIC res ns:', os.clock_getres(os.CLOCK_MONOTONIC)); print('MONOTONIC_RAW res ns:', os.clock_getres(os.CLOCK_MONOTONIC_RAW))"
echo '=== gpu ==='; nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader 2>/dev/null || echo 'no nvidia-smi'
echo '=== uname ==='; uname -sr; cat /etc/os-release | head -2
```

Mac 侧据输出定稿 `configs/platforms/gb10-spark-01.json`（控制组 CPU 编号以实测拓扑为准）+ `gb10-spark-01.capability.json`，push 后 GB10 `git pull` 继续。

## 2. 首跑（GB10 侧）

```bash
cd ~/cpu-uarch-explorer   # git pull 拿到平台配置后
.venv/bin/python -m runner.cli plan --experiment configs/experiments/ptr-chase-cache-sweep.json --platform configs/platforms/gb10-spark-01.json    # 先预览：28 case（14 档 × 2 控制组）
.venv/bin/python -m runner.cli run  --experiment configs/experiments/ptr-chase-cache-sweep.json --platform configs/platforms/gb10-spark-01.json
.venv/bin/python -m analysis.cli report --run data/public/runs/<run目录>
```

预期数分钟（28 case × 5 重复）。`raw/` 留在 GB10 本地（`data/public/runs/<run>/raw/`），其余打包回传。

## 3. 回传（GB10 打包 → USB-C → Mac 解包）

```bash
# GB10 侧：run 目录不含 raw/ 打包
RUN=$(ls -dt ~/cpu-uarch-explorer/data/public/runs/*ptr-chase-cache-sweep | head -1)
tar czf ~/gb10-run.tar.gz -C "$(dirname $RUN)" "$(basename $RUN)" --exclude=raw
# USB-C 拷到 Mac 后，Mac 侧：
mkdir -p data/quarantine && tar xzf gb10-run.tar.gz -C data/quarantine/
python3 scripts/quarantine_intake.py data/quarantine/<run目录>   # 通过则按提示移入 data/public/runs/
```

## 4. Mac 侧收口

quarantine 通过 → 移入 `data/public/runs/` → `uv run --with jsonschema` 复验 → 按提交粒度提交（数据 / 文档分开，CHANGELOG 单独提交）。

## 已知坑

- DGX OS 定制：cpufreq sysfs 可能缺失/只读——能力发现阶段如实记录 `no cpufreq sysfs` 即可（freq_snapshot 字段自动省略，不编造）。
- CPU/GPU 共享内存控制器：平台配置已声明 `aux_snapshots`（nvidia-smi GPU 利用率，run 前后入档）；若 GPU 有负载，数据按 MEDIUM 置信度标注。
- 不要在本仓目录内做 GB10 侧 git 提交；GB10 仓只是只读工作副本。
