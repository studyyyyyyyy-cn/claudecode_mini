# claude_code_mini

> 用 ~4000 行 Python 实现的轻量级 AI 编程助手，支持双 LLM 后端、上下文压缩、长期记忆、技能扩展、MCP 协议。

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 目录

- [环境要求](#环境要求)
- [安装](#安装)
- [配置 API](#配置-api)
- [快速开始](#快速开始)
- [命令行参数](#命令行参数)
- [REPL 内置命令](#repl-内置命令)
- [使用示例](#使用示例)
- [项目架构](#项目架构)
- [文件结构](#文件结构)
- [核心机制](#核心机制)
- [扩展方式](#扩展方式)
- [文档](#文档)

---

## 环境要求

| 项 | 要求 |
|----|------|
| Python | `>= 3.11` |
| 依赖 | `anthropic`, `openai`, `rich` |
| 网络 | 需访问 LLM API 端点 |

## 安装

```bash
git clone https://github.com/studyyyyyyyy-cn/claudecode_mini.git
cd claudecode_mini
pip install -e .
```

或只装依赖、直接用模块方式运行：

```bash
pip install anthropic openai rich
python -m mini_claude
```

## 配置 API

支持两种后端，任选其一。

### 方式一：Anthropic 官方 API

```bash
# Linux / macOS
export ANTHROPIC_API_KEY=sk-ant-...

# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

可选：自定义端点
```bash
export ANTHROPIC_BASE_URL=https://your-proxy.com
```

### 方式二：OpenAI 兼容 API（DeepSeek / AIHubMix 等）

```bash
# Linux / macOS
export OPENAI_API_KEY=sk-xxx
export OPENAI_BASE_URL=https://api.deepseek.com
export OPENAI_MODEL=deepseek-v4-flash

# Windows PowerShell
$env:OPENAI_API_KEY = "sk-xxx"
$env:OPENAI_BASE_URL = "https://api.deepseek.com"
$env:OPENAI_MODEL = "deepseek-v4-flash"
```

**优先级**：`OPENAI_API_KEY + OPENAI_BASE_URL` 同时存在 → 自动走 OpenAI 兼容模式；仅 `OPENAI_API_KEY` 存在 → 不自动切换，需配合 `--api-base` 参数。

### Windows 永久配置

```powershell
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-xxx", "User")
[Environment]::SetEnvironmentVariable("OPENAI_BASE_URL", "https://api.deepseek.com", "User")
[Environment]::SetEnvironmentVariable("OPENAI_MODEL", "deepseek-v4-flash", "User")
```

重启终端后生效。

---

## 快速开始

### 交互式 REPL

```bash
python -m mini_claude
```

启动后输入自然语言指令即可。`exit` 或 `quit` 退出。

### 一次性执行

```bash
python -m mini_claude "帮我查看当前目录有哪些 Python 文件"
python -m mini_claude "重构 tools.py 中的大函数"
```

### 跳过确认

```bash
python -m mini_claude --yolo "运行所有测试并修复失败的"
```

### 只读规划模式

```bash
python -m mini_claude --plan "分析 agent.py 的架构，给出重构方案"
```

### 恢复上次会话

```bash
python -m mini_claude --resume
```

---

## 命令行参数

| 参数 | 简写 | 说明 |
|------|------|------|
| `--yolo` | `-y` | 跳过所有确认提示 |
| `--plan` | - | 只读模式，只能编辑计划文件 |
| `--accept-edits` | - | 自动批准文件编辑，危险命令仍确认 |
| `--dont-ask` | - | 自动拒绝需确认的操作（CI 场景） |
| `--thinking` | - | 启用扩展思考（仅 Anthropic 模型） |
| `--model` | `-m` | 指定模型，覆盖环境变量和默认值 |
| `--api-base` | - | OpenAI 兼容 API 端点 URL |
| `--resume` | - | 恢复最近一次会话 |
| `--max-cost` | - | 费用上限（美元），超出后自动停止 |
| `--max-turns` | - | 最大对话轮数上限 |
| `--help` | `-h` | 显示帮助 |

---

## REPL 内置命令

| 命令 | 说明 |
|------|------|
| `/clear` | 清空对话历史 |
| `/plan` | 切换计划模式 |
| `/cost` | 查看 Token 用量和预估费用 |
| `/compact` | 手动触发对话压缩 |
| `/memory` | 列出所有已保存的记忆 |
| `/skills` | 列出所有可用技能 |
| `/<skill>` | 调用一个技能（如 `/commit`） |
| `exit` / `quit` | 退出 |

---

## 使用示例

### 代码探索

```
> 这个项目的主入口在哪里，怎么启动的？
  📖 read_file mini_claude/__main__.py
  [返回 main() 函数和参数解析逻辑]
  → 入口是 __main__.py 的 main() 函数，支持 REPL 和一次性两种模式...
```

### 代码修改

```
> 把 tools.py 里所有 print 改成 logging
  🔍 grep_search pattern="print\(" path=mini_claude/tools.py
  [返回 3 处匹配]
  🔧 edit_file mini_claude/tools.py
  [显示 diff：- print(...) → + logging.debug(...)]
```

### 任务追踪

```
> 我需要重构 agent.py，步骤比较多，帮我管理一下
  📋 task_create 分析 agent.py 现有结构
  📋 task_create 拆分大函数
  📋 task_create 添加错误处理
  Task created: [a1b2c3d4] 分析 agent.py 现有结构
  Task created: [e5f6g7h8] 拆分大函数
  Task created: [i9j0k1l2] 添加错误处理

> 开始做第一个
  🔧 task_update task_id=a1b2c3d4 status=in_progress
  Task [a1b2c3d4] updated: status=in_progress
```

### 子 Agent 并行

```
> 同时搜索三个模块里所有 TODO 注释
  🤖 grep_search "TODO" in agent.py ┐
  🤖 grep_search "TODO" in tools.py ├ 并行执行
  🤖 grep_search "TODO" in ui.py    ┘
```

---

## 项目架构

```
┌────────────────────────────────────────────┐
│              __main__.py                    │  入口：CLI 解析、REPL 循环
├────────────────────────────────────────────┤
│              agent.py                       │  核心：Agent 循环
│       ┌───────┼───────┐                   │
│   Anthropic  OpenAI   MCP                  │  双后端 + 外部协议
├────────────────────────────────────────────┤
│ tools.py │ prompt.py │ session.py          │
│ memory.py│ skills.py │ subagent.py         │  设施层
│ tasks.py │ mcp_client│ ui.py              │
├────────────────────────────────────────────┤
│          ~/.mini-claude/                    │  持久层（会话/记忆/任务均落盘）
└────────────────────────────────────────────┘
```

**核心流程**：用户输入 → 消息队列 → LLM API → 返回文本或工具调用 → 权限检查 → 执行工具 → 结果注入对话 → 循环，直到 LLM 返回纯文本结束。

---

## 文件结构

```
mini_claude/
├── __init__.py         # 版本号
├── __main__.py         # CLI 入口、REPL 循环、参数解析
├── agent.py            # Agent 核心循环、双后端、压缩管道、计划模式、子 Agent 调度
├── tools.py            # 13 个工具定义与执行、5 级权限系统、危险命令检测
├── prompt.py           # 系统提示词模板、CLAUDE.md 加载、Git 上下文注入
├── session.py          # 对话历史 JSON 持久化
├── memory.py           # 4 类型长期记忆、语义检索、自动索引
├── skills.py           # 技能系统（Markdown 模板、inline/fork 执行）
├── subagent.py         # 子 Agent 系统（内置 3 类 + 自定义）
├── tasks.py            # 任务追踪（创建/列表/更新、JSON 持久化）
├── mcp_client.py       # MCP 协议客户端（stdio JSON-RPC）
├── ui.py               # 终端渲染（彩色输出、旋转动画、diff 高亮）
└── frontmatter.py      # YAML frontmatter 解析
```

---

## 核心机制

### 双 LLM 后端

| | Anthropic | OpenAI 兼容 |
|--|-----------|-------------|
| SDK | `anthropic` | `openai` |
| 协议 | `/v1/messages` | `/v1/chat/completions` |
| 流式工具 | `content_block_stop` 立即执行 | delta 组装后批量执行 |
| 思考模式 | ✅ | ❌ |

检测到 `OPENAI_BASE_URL` 环境变量或 `--api-base` 参数时自动切换。

### 上下文压缩（5 层）

| 层 | 触发条件 | 动作 |
|----|----------|------|
| Tier 0 | 单结果 > 30KB | 写磁盘，只留 200 行预览 |
| Tier 1 | 利用率 > 50% | 超长结果保留头尾，中间截断 |
| Tier 2 | 利用率 > 60% | 旧搜索/读结果 → `[Content snipped]` |
| Tier 3 | 空闲 > 5min | 更激进清除 → `[Old result cleared]` |
| Tier 4 | 利用率 > 85% | LLM 摘要整段对话，重建历史 |

### 权限系统（5 级）

```
bypassPermissions → acceptEdits → default → dontAsk → plan
   全部放行          自动接编辑      默认     自动拒绝    全只读
```

每级通过决策树判断：配置文件禁止/允许规则 → 只读工具自动放行 → 计划模式沙箱 → 危险命令确认。

### 记忆系统

4 类记忆（用户画像/反馈纠正/项目背景/参考链接）以 Markdown + 元数据头存储。每轮对话后台异步检索相关记忆，匹配结果自动注入对话，超过一天的记忆附带时效警告。

### 扩展系统

| 扩展方式 | 形式 | 是否需要写代码 |
|----------|------|:------------:|
| 技能 | `.claude/skills/<name>/SKILL.md` | ❌ |
| 自定义子 Agent | `.claude/agents/<name>.md` | ❌ |
| MCP 服务器 | `settings.json` 配置 + 外部进程 | 配置不需要 |

---

## 扩展方式

### 添加技能

```bash
mkdir -p .claude/skills/commit
```

创建 `.claude/skills/commit/SKILL.md`：

```markdown
---
name: commit
description: 生成约定式提交信息并提交
user-invocable: true
context: inline
allowed-tools: read_file, run_shell
---

分析 `git diff --staged`，生成符合 Conventional Commits 规范的提交信息并执行提交。
```

然后 `/commit` 即可调用。

### 添加自定义子 Agent

```bash
mkdir -p .claude/agents
```

创建 `.claude/agents/reviewer.md`：

```markdown
---
name: reviewer
description: 代码审查
allowed-tools: read_file, list_files, grep_search
---

你是资深审查者。关注正确性、安全性、可维护性，返回结构化报告。
```

Agent 在需要时可自动调用 `agent(type="reviewer", ...)`。

### 连接 MCP 服务器

在 `.claude/settings.json` 添加：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"]
    }
  }
}
```

工具会自动以 `mcp__filesystem__` 前缀注册。

---

## 文档

| 文档 | 说明 |
|------|------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 架构设计、上下文管理、记忆机制、安全权限、扩展机制深度解析 |
| [DOCS.md](./DOCS.md) | 面向新手的完整实现文档，从架构到每个函数 |
