# 08 · 落盘可靠性：崩溃、断电与"半成品文件"

> 费曼段：一句话——**写文件像寄信：先写好放门口（tmp），确认封好（fsync），再一次性换进信箱（replace），最后告诉邮局（父目录 fsync）。**

## 概念

### 两种写盘，两种原子性策略

1. **records.jsonl（流水账）**：逐行**追加**，每行写完立刻 `flush + fsync`。跑到一半断电，最多丢当前这一行，已完成的 case 全部安全。
2. **manifest 等汇总文件（一次成型）**：先写 `xxx.tmp` → fsync → `os.replace()` 原子改名 → 父目录 fsync。读者要么看到完整的新文件，要么看到不存在——**永远看不到写了一半的文件**。

### 为什么不能"直接写"

`os.replace` 在同文件系统内是原子操作（ rename 语义）；`fsync` 确保数据真的进了存储而不是躺在内核缓存；父目录 fsync 确保**目录项**（文件名 → inode 的映射）也落了盘。少任何一步，崩溃后就可能出现：文件内容是新的但名字没生效、名字生效但内容是旧的、或者干脆是 0 字节。

### 原始样本的完整性与"不入库"

每个 sample 的原始 stdout/stderr 落盘并算 SHA256 进 artifact-manifest——任何记录里的数字都能顺着 `raw_samples_ref` 找回原始输出。但 raw/ **不进 git**（占 run 目录 83% 体量、可再生）：SHA256 锚定完整性，需要时按记录参数重跑再生。git 只收 records/manifests——那是数据层本体。

### 一个真实的回归教训

`Path("case.s0").with_suffix(".stdout.txt")` 会把 `.s0` 当成文件后缀**替换掉**——同 case 的 5 趟样本互相覆盖，只剩最后一趟。修复用字符串拼接，并加了回归测试（`test_artifacts.py`：5 个样本必须产出 10 个文件且 SHA256 互不相同）。

## 费曼自测

1. 为什么追加写适合流水、原子替换适合汇总？（流水要求中途崩溃少丢数据；汇总要求读者不见半成品）
2. 为什么 fsync 了文件还要 fsync 目录？（文件名→inode 的映射本身也是数据，存在目录里）
3. raw 不入库后，审计怎么进行？（manifest 的 SHA256 + 记录参数可重跑核对）

## 锚点

- `runner/records.py`（JsonlWriter / write_json_atomic）
- `runner/artifacts.py`、`runner/tests/test_artifacts.py`
- 数据策略：v0.3 §7（runs 管理）
