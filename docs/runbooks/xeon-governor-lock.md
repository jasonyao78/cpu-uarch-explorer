# Runbook：Xeon 锁频测量（环境事务接线后的两条路径）

> 背景：powersave 下指针追逐全程 800MHz 不升频（`data/public/runs/20260924T184842Z` freq_snapshot 实证）——计时法 ns 绝对值不可跨档比较。锁频 = host 级状态突变，**必须走环境事务**（journal 留痕、逆序恢复、中断 reconcile）。
> 口径声明（任务书 §5.5）：performance **不等于固定频率**——turbo/热漂移仍在，records 带 freq_snapshot 如实入档，报告写"已锁 performance 档，实测频率见快照"。

## 路径 A：工具全自动（需一次性 sudoers 授权）

非交互通道不挂起等密码，controller 经 `sudo -n` 执行；无免密 sudo 时给出结构化 `env-apply-failed`（已实证，系统不被改变）。一次性配置（人工，在 Xeon 上）：

```bash
# 1. 包装脚本：参数白名单（performance/powersave 二字），root 属主防篡改
sudo tee /usr/local/bin/cpu-uarch-set-governor > /dev/null <<'EOF'
#!/bin/sh
# 用法: cpu-uarch-set-governor performance|powersave；写全部 CPU 的 scaling_governor
case "$1" in
  performance|powersave) ;;
  *) echo "usage: $0 performance|powersave" >&2; exit 1 ;;
esac
for c in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo "$1" | tee "$c" > /dev/null || exit 1
done
EOF
sudo chown root:root /usr/local/bin/cpu-uarch-set-governor
sudo chmod 755 /usr/local/bin/cpu-uarch-set-governor

# 2. sudoers 单命令白名单 + 语法校验
echo 'michael ALL=(ALL) NOPASSWD: /usr/local/bin/cpu-uarch-set-governor' | sudo tee /etc/sudoers.d/cpu-uarch-probe
sudo visudo -c -f /etc/sudoers.d/cpu-uarch-probe

# 3. 验证免密可用
sudo -n /usr/local/bin/cpu-uarch-set-governor performance && cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
sudo -n /usr/local/bin/cpu-uarch-set-governor powersave    # 测完即还原
```

> 安全面：免密 sudo 仅限这一个脚本；脚本内参数白名单使滥用也只能在
> performance/powersave 间切换（完全可逆、无破坏面）；脚本 root 属主 +
> 755 防篡改扩权。controller 经 `sudo -n` 调此脚本（已接线）。

```bash
# 锁频测量（apply → sweep → 自动逆序 restore；中断后下次 run 自动 reconcile）
.venv/bin/python -m runner.cli run \
  --experiment configs/experiments/ptr-chase-cache-sweep.json \
  --platform configs/platforms/xeon-8481c-01.json \
  --env governor=performance --allow-mutation
```

## 路径 B：人工 sudo（当前可用，零配置变更）

```bash
# Xeon 上（先锁，测完恢复）
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null
# Mac 上正常 run（不带 --env；freq_snapshot 验证频率档）
.venv/bin/python -m runner.cli run --experiment configs/experiments/ptr-chase-cache-sweep.json \
  --platform configs/platforms/xeon-8481c-01.json
# 测完恢复
echo powersave | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null
```

历史人工锁频数据：`20260924T185031Z`（4K）与 `20260924T184842Z`（hp2m，参考基线）。

## 中断与恢复语义（已测试钉住）

- `kill -INT` 中断 run → 事务捕获 KeyboardInterrupt → 逆序 restore → 重抛；
- 下次 `run --env` 启动时自动 `reconcile_unfinished`：检测残留 journal 并完成 restore（SIGINT 场景实证）；SIGKILL 场景靠"未完成事务阻塞 + 启动 reconcile"兜底；
- 恢复失败（如 sudo 密码失效）→ 结构化拒绝运行，人工 `runner.cli env status / restore --tx <id>`。

## 声明式（可选）

平台配置顶层加 `"host_requirements": {"cpufreq.governor": "performance"}` 后，普通 `run --allow-mutation` 即自动锁频（schema README 已登记）。**当前未对 xeon 配置开启**——在 sudoers 配好前开启会让所有日常 run 撞 sudo 失败。
