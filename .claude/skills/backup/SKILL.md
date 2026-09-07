---
name: backup
description: Use when the user wants to back up or restore ScholarAIO data through configured rsync targets, inspect backup plans, or run a dry-run before transferring files.
---
# Backup / 数据备份

通过 `scholaraio backup` 统一执行远程 rsync 增量备份与完整实例恢复。

## 目标

- 不要让 agent 直接手写一长串 `rsync` 命令
- 优先复用 `config.yaml` / `config.local.yaml` 中的命名备份目标
- 对真实传输前，优先建议先做一次 `--dry-run`
- 区分兼容的 `data` 范围与可恢复的 `instance` 范围

## 使用方式

先查看已配置目标：

```bash
scholaraio backup list
```

执行某个备份目标：

```bash
scholaraio backup run <target>
```

预演模式：

```bash
scholaraio backup run <target> --dry-run
```

恢复完整实例：

```bash
scholaraio backup restore <target> --destination <instance-dir> --dry-run
scholaraio backup restore <target> --destination <instance-dir>
```

## 配置约定

在 `config.yaml` 中：

```yaml
backup:
  source_dir: data
  targets:
    lab:
      host: backup.example.com
      user: alice
      path: /srv/scholaraio
      port: 22
      identity_file: ~/.ssh/id_ed25519
      scope: instance
      mode: default
      compress: true
      enabled: true
      exclude:
        - "*.tmp"
```

建议：

- `scope: data` 只同步 `source_dir`，保持旧行为；`scope: instance` 同步 config、data、workspace、published 和 control metadata，并生成恢复清单
- 真实 `instance` 备份会对组件树中的 `.db` / `.sqlite` / `.sqlite3` 使用 SQLite online backup，并在传输前执行 `quick_check`；不会把 live WAL/SHM/journal sidecar 当作恢复数据
- `connect_timeout_seconds`、`io_timeout_seconds`、`process_timeout_seconds` 分别限制 SSH 建连、空闲 I/O 和单个外部进程总时长
- 共享配置写在 `config.yaml`
- 主机相关或敏感项优先放 `config.local.yaml`
- 备份整棵 `data/` 目录时优先使用 `default`
- 只有在明确备份对象是追加型文件时，才考虑 `append` / `append-verify`
- `instance` 范围必须使用 `mode: default`、不得配置 `exclude`，并应使用专用的空远端目录
- 密钥目标使用非交互 SSH（`BatchMode=yes`）；密码目标使用内部 `SSH_ASKPASS`；两种模式都不会交互确认 host key
- 如果远端只接受密码，可以只在 `config.local.yaml` 里为该 target 写 `password`；ScholarAIO 会自动切到内部 askpass 路径
- `instance` 会备份 `config.local.yaml`。SSH 只保护传输过程；API Key 和密码在远端仍是明文文件，因此必须保护远端账号和存储权限
- 仅存在于环境变量中的 API Key 不会进入备份；需要恢复的密钥必须持久化到 `config.local.yaml`
- 新机器恢复时，先提供能连接远端的最小 target 配置，再执行 restore；恢复后的 `config.local.yaml` 会覆盖 bootstrap 配置
- 可直接引导用户执行：`ssh-keyscan -p <port> <host> >> ~/.ssh/known_hosts`，再执行：`ssh -i <identity_file> -p <port> <user>@<host> true`

## Agent 行为规范

1. 先运行 `scholaraio backup list` 确认目标存在
2. 首次执行某个目标，优先建议用户先做 `--dry-run`
3. 如果用户明确要求立即备份，再执行真实同步
4. 恢复前先执行 `backup restore ... --dry-run`；目标非空时除非用户明确同意合并，否则不要添加 `--force`
5. 如果 CLI 返回非零退出码，向用户转述 rsync/ssh 失败信息，不要自己编造原因
6. 遇到认证失败或 host key 未预置信任时，优先提醒用户去更新 `config.local.yaml` / SSH 配置，而不是要求用户在 CLI 里临时输入参数

## 何时不用这个 skill

- 用户只是想一般性讨论“备份策略怎么设计”而不是立即执行
- 用户要做本地压缩打包或快照归档，而不是远程 rsync 同步/恢复
