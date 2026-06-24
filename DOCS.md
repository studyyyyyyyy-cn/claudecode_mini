# claude_code_mini — 从零开始的 AI 编程助手

> 读完本文档，你将理解一个 AI 编程助手是怎么从代码层面实现的。

---

## 目录

1. [这是什么？](#1-这是什么)
2. [总体架构](#2-总体架构)
3. [一次对话的完整旅程](#3-一次对话的完整旅程)
4. [模块详解](#4-模块详解)
   - [4.1 `__main__.py` — 程序入口](#41-__main__py--程序入口)
   - [4.2 `agent.py` — 大脑](#42-agentpy--大脑核心循环)
   - [4.3 `tools.py` — 工具箱](#43-toolspy--工具箱)
   - [4.4 `prompt.py` — 系统提示词](#44-promptpy--系统提示词)
   - [4.5 `ui.py` — 终端界面](#45-uipy--终端界面)
   - [4.6 `session.py` — 会话管理](#46-sessionpy--会话管理)
   - [4.7 `memory.py` — 记忆系统](#47-memorypy--记忆系统)
   - [4.8 `skills.py` — 技能系统](#48-skillspy--技能系统)
   - [4.9 `subagent.py` — 子 Agent](#49-subagentpy--子-agent)
   - [4.10 `tasks.py` — 任务追踪](#410-taskspy--任务追踪)
   - [4.11 `mcp_client.py` — MCP 客户端](#411-mcp_clientpy--mcp-客户端)
   - [4.12 `frontmatter.py` — 元数据解析](#412-frontmatterpy--元数据解析)
5. [数据流向图](#5-数据流向图)
6. [如何扩展](#6-如何扩展)

---

## 1. 这是什么？

**claude_code_mini** 是一个用 Python 写的 AI 编程助手。你在终端里用自然语言告诉它要做什么（比如"帮我修 bug"、"重构这个文件"），它会自动读代码、写代码、搜文件、执行命令，直到任务完成。

它模仿了 Anthropic 公司的 [Claude Code](https://github.com/anthropics/claude-code) 的核心架构，但只用 ~4000 行 Python 就实现了关键功能。

### 能做什么？

- 📖 读文件、搜索代码
- ✏️ 写文件、修改代码
- 💻 执行 Shell 命令
- 🌐 抓取网页
- 🧠 记住你的偏好（记忆系统）
- 📋 跟踪复杂任务进度
- 🔀 派子 Agent 并行干活
- 🔌 连接 MCP 服务器扩展能力

---

## 2. 总体架构

```
┌─────────────────────────────────────────────┐
│                  __main__.py                 │  ← 入口：解析参数，启动 REPL 或一次性执行
│              (CLI + 交互循环)                  │
└──────────────────┬──────────────────────────┘
                   │ 创建并调用
┌──────────────────▼──────────────────────────┐
│                  agent.py                    │  ← 大脑：LLM 调用、工具执行、上下文压缩
│           (Agent 核心循环 + 双后端)             │
└────┬──────────┬──────────┬──────────┬───────┘
     │          │          │          │
     ▼          ▼          ▼          ▼
┌─────────┐ ┌───────┐ ┌─────────┐ ┌──────────┐
│ tools.py │ │prompt │ │memory.py│ │session.py│
│ 13个工具  │ │ .py   │ │ 记忆系统 │ │ 会话持久化 │
└─────────┘ └───────┘ └─────────┘ └──────────┘
     │
     ├──► skills.py   技能系统
     ├──► subagent.py  子Agent
     ├──► tasks.py    任务追踪
     ├──► mcp_client  MCP协议
     └──► ui.py      终端渲染
```

**核心思想**：Agent 是一个无限循环——

1. 用户输入 → 附加到对话历史
2. 发送给 LLM（大语言模型）
3. LLM 返回文字或工具调用
4. 如果是文字 → 打印给用户，结束本轮
5. 如果是工具调用 → 执行工具，结果附加到对话历史，回到步骤 2

---

## 3. 一次对话的完整旅程

假设你输入：**"帮我重构 agent.py，把大函数拆分"**

```
用户终端输入
    │
    ▼
__main__.py  run_repl()
    │ 读到 "帮我重构 agent.py"
    │ 调用 agent.chat(user_message)
    ▼
agent.py  _chat_openai() 或 _chat_anthropic()
    │ 1. 检查上下文是否快满了 → 需要则压缩
    │ 2. 异步启动记忆召回（后台线程）
    │ 3. 构建请求 → 发给 LLM
    ▼
LLM 返回：
    "我先看看 agent.py 的结构"
    + tool_use: read_file("agent.py")
    │
    ▼
agent.py  解析响应
    │ 打印 LLM 的文字
    │ 发现 tool_use → 进入工具执行流程
    ▼
agent.py  _execute_tool_call("read_file", {"file_path": "agent.py"})
    │ 1. 权限检查 → read_file 属于 READ_TOOLS → 自动放行
    │ 2. 调用 execute_tool() → _read_file() → 返回文件内容
    │ 3. 结果附加到对话历史
    ▼
第二轮 LLM 请求（带上文件内容）
    │
    ▼
LLM 返回：
    "我发现 agent.py 的 chat 方法太长了，可以拆分成 chat、聊天逻辑、
     工具执行三个方法。开始修改..."
    + tool_use: edit_file("agent.py", old_str="...", new_str="...")
    │
    ▼
agent.py  权限检查 → edit_file 需要确认 → 弹出 "(y/n)"
    │ 用户按 y
    ▼
agent.py  _execute_tool_call → _edit_file() → 修改成功
    │
    ▼
继续循环，直到 LLM 不再调用工具，输出总结文字 → 结束
```

---

## 4. 模块详解

### 4.1 `__main__.py` — 程序入口

启动时发生的事情：

```
main()
 ├── parse_args()          解析命令行参数（--yolo, --plan, --model 等）
 ├── _resolve_permission_mode()  确定权限模式
 ├── 读取环境变量             决定用 OpenAI 还是 Anthropic 后端
 ├── 选择模型                 OpenAI → OPENAI_MODEL 或 gpt-4o
 │                          Anthropic → claude-opus-4-6
 ├── Agent(...)             创建 Agent 实例
 └── 两个分支：
     ├── 有 prompt → asyncio.run(agent.chat(prompt))  一次性执行
     └── 无 prompt → asyncio.run(run_repl(agent))     交互式 REPL
```

**关键函数：**

| 函数 | 作用 |
|------|------|
| `parse_args()` | 解析 CLI 参数，支持 `--yolo` `--plan` `--thinking` `--model` `--api-base` `--resume` `--max-cost` `--max-turns` |
| `_resolve_permission_mode(args)` | `--yolo` → bypassPermissions, `--plan` → plan, `--accept-edits` → acceptEdits, `--dont-ask` → dontAsk, 默认 default |
| `run_repl(agent)` | 交互式主循环：显示提示符、读取输入、处理 `/` 命令（/clear /plan /cost /compact /memory /skills）、调用 skill、普通对话 |
| `main()` | 顶层入口，串联以上所有步骤 |

**REPL 内置命令：**

| 命令 | 功能 |
|------|------|
| `/clear` | 清空对话历史，释放上下文 |
| `/plan` | 切换计划模式（只读 vs 正常） |
| `/cost` | 显示 Token 用量和费用估算 |
| `/compact` | 手动压缩对话上下文 |
| `/memory` | 列出所有已保存的记忆 |
| `/skills` | 列出所有可用技能 |
| `/<skill>` | 调用一个技能 |
| `exit` / `quit` | 退出程序 |

---

### 4.2 `agent.py` — 大脑（核心循环）

这是整个项目最核心的模块（~1300 行），实现了 AI 编程助手的完整循环。

#### 4.2.1 Agent 类 —— 构造函数

```python
class Agent:
    def __init__(self, *, permission_mode, model, api_base, api_key,
                 thinking, max_cost_usd, max_turns, confirm_fn, ...)
```

创建时初始化：
- **双客户端**：根据是否有 `api_base` 决定用 OpenAI SDK 还是 Anthropic SDK
- **对话历史**：`_anthropic_messages` 或 `_openai_messages` 列表
- **工具列表**：从 `tools.py` 加载 13 个工具定义
- **系统提示词**：从 `prompt.py` 动态构建
- **压缩参数**：上下文窗口大小、压缩阈值
- **MCP 管理器**：延迟连接外部 MCP 服务器
- **记忆状态**：已召回的记忆集合、会话记忆字节数

#### 4.2.2 双后端设计

项目同时支持两种 LLM API 协议：

| 后端 | 协议 | SDK | 入口函数 |
|------|------|-----|----------|
| Anthropic | Anthropic Messages API | `anthropic.AsyncAnthropic` | `_chat_anthropic()` |
| OpenAI 兼容 | Chat Completions API | `openai.AsyncOpenAI` | `_chat_openai()` |

切换方式：只要设置了 `--api-base` 或 `OPENAI_BASE_URL` 环境变量，就自动使用 OpenAI 兼容模式。

**Anthropic 后端关键函数：**

| 函数 | 作用 |
|------|------|
| `_chat_anthropic(user_message)` | Anthropic 后端的完整一轮对话循环：添加用户消息 → 检查压缩 → 启动记忆预取 → 调用 LLM 流式接口 → 处理工具调用 → 循环 |
| `_call_anthropic_stream(on_tool_block_complete)` | 流式调用 Anthropic API。边接收边打印文字。当某个 tool_use 块完成时，如果它是并发安全的工具，**不等整个响应结束就立即开始执行**（流式工具执行） |
| `_block_to_dict(block)` | 把 Anthropic 的 content block 对象转成可序列化的 dict（用于存储到对话历史） |

**OpenAI 兼容后端关键函数：**

| 函数 | 作用 |
|------|------|
| `_chat_openai(user_message)` | OpenAI 后端的完整一轮对话循环：添加用户消息 → 检查压缩 → 启动记忆预取 → 调用 LLM 流式接口 → 工具分组并行执行 → 循环 |
| `_call_openai_stream()` | 流式调用 OpenAI API。手动解析 SSE 流，组装 tool_calls JSON（OpenAI 流式返回的 tool_calls 是增量 delta） |
| `_to_openai_tools(tools)` | 把 Anthropic 格式的工具定义转成 OpenAI 的 `function` 格式 |

#### 4.2.3 工具执行与权限

```
_execute_tool_call(name, input)
    │
    ├── name == "enter_plan_mode" / "exit_plan_mode" → _execute_plan_mode_tool()
    ├── name == "agent" → _execute_agent_tool()  (派子 Agent)
    ├── name == "skill" → _execute_skill_tool()  (执行技能)
    ├── name 以 "mcp__" 开头 → mcp_manager.call_tool()  (MCP 工具)
    └── 其他 → execute_tool() (tools.py)
```

**权限检查流程（每个工具调用前）：**

```
check_permission(tool_name, input, mode)
    │
    ├── bypassPermissions → 直接放行
    ├── 查 settings.json 的 deny 规则 → 命中则拒绝
    ├── 查 settings.json 的 allow 规则 → 命中则放行
    ├── tool 在 READ_TOOLS 中 → 自动放行
    ├── plan 模式 + 编辑工具 → 只允许编辑计划文件
    ├── 危险命令 (rm, sudo, git push 等) → 需确认
    ├── 新建文件 → 需确认
    └── 其他 → 放行
```

**Anthropic 后端的流式工具并行执行（`agent.py:897-904`）：**

在 Anthropic 后端，LLM 返回的是一个流。当某个 `tool_use` 块在流中完成时（`content_block_stop` 事件），如果该工具在 `CONCURRENCY_SAFE_TOOLS` 中且权限检查通过，就**立即创建异步任务开始执行**，不用等整个响应结束。这意味着 LLM 还在生成下一个工具调用时，前一个已经在跑了。

#### 4.2.4 4 层上下文压缩

LLM 的上下文窗口有限（比如 200K tokens）。对话越长，历史越多，越容易超过窗口。压缩系统分 4 层：

| 层级 | 触发条件 | 做什么 | 对应函数 |
|------|----------|--------|----------|
| **Tier 0: 大结果持久化** | 工具结果 > 30KB | 写磁盘，上下文中只留 200 行预览 + 路径 | `_persist_large_result()` |
| **Tier 1: 预算裁剪** | 上下文利用率 > 50% | 裁剪超长工具结果，保留头尾，中间截断 | `_budget_tool_results_*()` |
| **Tier 2: 旧结果替换** | 上下文利用率 > 60% | 旧的搜索/读文件结果替换为占位符 `[Content snipped]`，保留最近 3 个 | `_snip_stale_results_*()` |
| **Tier 3: 微压缩** | 距上次 API 调用 > 5 分钟 | 清除更旧的工具结果 | `_microcompact_*()` |
| **完全压缩** | 上下文利用率 > 85% | 调用 LLM 把整个对话总结成一个段落，重建对话历史 | `_compact_anthropic()` / `_compact_openai()` |

```
调用顺序：
_check_and_compact()        ← 每轮对话开始时检查（>85% 触发完全压缩）
    └── _compact_conversation()
_run_compression_pipeline()  ← 每轮 LLM 调用前执行
    ├── Tier 1: _budget_tool_results()
    ├── Tier 2: _snip_stale_results()
    └── Tier 3: _microcompact()
```

#### 4.2.5 计划模式

```
toggle_plan_mode()
    │
    ├── 进入 plan 模式：保存当前权限模式 → 切换为 plan
    │   系统提示词注入 Plan Mode 指令
    │   告诉 LLM：只能读文件，只能编辑计划文件
    │
    └── 退出 plan 模式：
        _execute_plan_mode_tool("exit_plan_mode")
        ├── 读取计划文件内容
        ├── 弹出 4 个选项给用户：
        │   1) 清空上下文 + 执行
        │   2) 保留上下文 + 自动接受编辑
        │   3) 保留上下文 + 手动确认每个编辑
        │   4) 继续修改计划
        └── 按用户选择恢复权限模式 + 执行
```

#### 4.2.6 其他重要功能

| 功能 | 函数 | 说明 |
|------|------|------|
| 重试 | `_with_retry(fn, max_retries=3)` | 指数退避重试，处理 429/503/529 等可重试错误 |
| 预算控制 | `_check_budget()` / `_get_current_cost_usd()` | 按 Token 估算费用，超出 `--max-cost` 或 `--max-turns` 自动停止 |
| 中断 | `abort()` | Ctrl+C 中断当前 LLM 调用 |
| 思考模式 | `_resolve_thinking_mode()` | Anthropic 模型支持 extended thinking（扩展思考），检测模型能力自动启用 |
| 记忆预取 | 异步 `start_memory_prefetch()` | 每轮用户输入后，后台调用小模型语义匹配相关记忆，匹配完成后注入到对话 |

---

### 4.3 `tools.py` — 工具箱

13 个工具，5 种权限模式。

#### 4.3.1 工具总览

| 工具 | 类型 | 函数 | 功能 |
|------|------|------|------|
| `read_file` | 读 | `_read_file(file_path)` | 读取文件，带行号返回 |
| `write_file` | 写 | `_write_file(file_path, content)` | 创建/覆盖文件，返回预览 |
| `edit_file` | 写 | `_edit_file(file_path, old_string, new_string)` | 精确字符串替换编辑 |
| `list_files` | 读 | `_list_files(pattern, path)` | Glob 模式匹配文件列表 |
| `grep_search` | 读 | `_grep_search(pattern, path, include)` | 正则搜索文件内容 |
| `run_shell` | 执行 | `_run_shell(command, timeout)` | 执行 Shell 命令 |
| `web_fetch` | 读 | `_web_fetch(url, max_length)` | 抓取 URL，自动剥离 HTML 标签 |
| `skill` | 特殊 | (在 agent.py 中处理) | 调用已注册的技能 |
| `enter_plan_mode` | 特殊 | (在 agent.py 中处理) | 进入只读计划模式 |
| `exit_plan_mode` | 特殊 | (在 agent.py 中处理) | 退出计划模式，提交计划审批 |
| `agent` | 特殊 | (在 agent.py 中处理) | 派生子 Agent 执行任务 |
| `task_create` | 写 | `_task_create(subject, description)` | 创建新任务，返回 8 位 ID |
| `task_list` | 读 | `_task_list()` | 列出所有任务及其状态 |
| `task_update` | 写 | `_task_update(task_id, status, ...)` | 更新任务状态或内容 |
| `tool_search` | 读 | (在 execute_tool 中处理) | 搜索并激活延迟加载的工具 |

#### 4.3.2 工具分类

```python
READ_TOOLS    = {read_file, list_files, grep_search, web_fetch, task_list}
EDIT_TOOLS    = {write_file, edit_file}
CONCURRENCY_SAFE_TOOLS = {read_file, list_files, grep_search, web_fetch, task_list}
```

- **READ_TOOLS**：自动放行，不需要用户确认
- **CONCURRENCY_SAFE_TOOLS**：可以多个并行执行（纯读取，无副作用）
- **EDIT_TOOLS**：需要权限检查（plan 模式禁止，default 模式新建文件需确认）

#### 4.3.3 工具执行流程

```
execute_tool(name, input, read_file_state)
    │
    ├── name == "read_file" → _read_file()  记录文件 mtime 到 read_file_state
    ├── name in (write_file, edit_file) → 检查 read-before-edit 规则
    │    ├── 没读过 → "Error: 请先用 read_file 读取该文件"
    │    └── 外部修改过 → "Warning: 文件已被外部修改，请重新读取"
    ├── name == "tool_search" → 搜索延迟工具并激活
    ├── 查 handlers dict → 调用对应函数
    └── 结果用 _truncate_result() 截断（最多 50000 字符）
```

#### 4.3.4 权限规则系统

权限规则来自两个 JSON 文件（合并，项目级覆盖用户级）：

- `~/.claude/settings.json`（用户全局）
- `.claude/settings.json`（项目级）

```json
{
  "permissions": {
    "allow": ["read_file(*)", "run_shell(npm test)"],
    "deny":  ["run_shell(rm *)", "write_file(/etc/*)"]
  }
}
```

规则格式：`工具名(匹配模式)`。模式支持 `*` 通配符前缀匹配。

#### 4.3.5 edit_file 的智能匹配

```
_edit_file(file_path, old_string, new_string)
    │
    ├── 在文件中搜索 old_string
    ├── 找不到？尝试 Unicode 引号归一化（中文引号 → 英文引号）
    ├── 找到多处？报错（必须唯一）
    ├── 替换后生成 diff（@@ -行号 +行号 @@ 格式）
    └── 写回文件 + 返回 diff
```

#### 4.3.6 危险命令检测

`is_dangerous(command)` 用正则匹配以下模式：
`rm`, `git push/reset/clean`, `sudo`, `mkfs`, `dd`, `>/dev/`, `kill`, `pkill`, `reboot`, `shutdown`, `del`, `rmdir`, `format`, `taskkill`, `Remove-Item`, `Stop-Process`

这些命令在执行前会弹出 (y/n) 确认。

---

### 4.4 `prompt.py` — 系统提示词

系统提示词是 LLM 的"角色设定"——告诉它它是谁、能做什么、怎么做。

#### 4.4.1 模板变量替换

```python
SYSTEM_PROMPT_TEMPLATE = """
You are Mini Claude Code...

# Environment
Working directory: {{cwd}}
Date: {{date}}
Platform: {{platform}}
Shell: {{shell}}
{{git_context}}      ← 分支名、最近提交、git status
{{claude_md}}        ← 项目的 CLAUDE.md 指令（含 @include 引用）
{{memory}}           ← 记忆索引（MEMORY.md）
{{skills}}           ← 可用技能列表
{{agents}}           ← 自定义子 Agent 列表
{{deferred_tools}}   ← 延迟加载的工具名
"""
```

`build_system_prompt()` 函数用当前运行时信息替换所有 `{{...}}` 占位符。

#### 4.4.2 CLAUDE.md 加载链

```
load_claude_md()
    │
    ├── 从 cwd 向上遍历到根目录
    │   查找每个目录的 CLAUDE.md → 合并（子目录在前，父目录在后）
    │
    ├── @include 解析：CLAUDE.md 可以引用其他文件
    │   @./local.md    → 相对于当前 CLAUDE.md 所在目录
    │   @~/global.md   → 相对于用户主目录
    │   @/absolute.md  → 绝对路径
    │   最大嵌套深度 5 层，检测循环引用
    │
    └── .claude/rules/*.md 加载（项目规则目录）
```

#### 4.4.3 Git 上下文

`get_git_context()` 运行 3 个 git 命令（3 秒超时）：
- `git rev-parse --abbrev-ref HEAD` → 当前分支名
- `git log --oneline -5` → 最近 5 条提交
- `git status --short` → 工作区状态

---

### 4.5 `ui.py` — 终端界面

基于 `rich` 库的彩色终端输出。全局只有一个 `Console` 实例。

| 函数 | 效果 |
|------|------|
| `print_welcome()` | 青色标题 + 使用提示 |
| `print_user_prompt()` | 绿色 `>` 提示符 |
| `print_assistant_text(text)` | 实时流式打印 LLM 输出 |
| `print_tool_call(name, inp)` | 黄色图标 + 工具名 + 摘要（如 📖 read_file agent.py） |
| `print_tool_result(name, result)` | 灰色结果，文件变更显示 diff 高亮（红删绿增） |
| `print_confirmation(cmd)` | 黄色 ⚠ + 危险命令 |
| `print_error(msg)` | 红色错误 |
| `print_info(msg)` | 青色 ℹ 信息 |
| `print_cost(in, out)` | Token 用量和美元费用 |
| `print_retry(attempt, max, reason)` | 黄色重试提示 |
| `print_plan_for_approval(content)` | 计划审批展示（最多 60 行） |
| `print_plan_approval_options()` | 4 个选项菜单 |
| `print_sub_agent_start/end(type, desc)` | 洋红色子 Agent 边界 |
| `start_spinner()` / `stop_spinner()` | Braille 字符旋转动画 "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"，80ms 一帧 |
| `print_divider()` | 灰色分割线 |

---

### 4.6 `session.py` — 会话管理

把对话历史存到 `~/.mini-claude/sessions/<session_id>.json`。

| 函数 | 作用 |
|------|------|
| `save_session(id, data)` | 保存会话（对话历史 + 元数据） |
| `load_session(id)` | 读取会话 |
| `list_sessions()` | 列出所有历史会话（只返回元数据） |
| `get_latest_session_id()` | 获取最新会话的 ID，用于 `--resume` |

Agent 每轮对话结束后自动调用 `_auto_save()` → `save_session()`。

---

### 4.7 `memory.py` — 记忆系统

让 Agent 能在对话之间记住你的偏好、项目背景等信息。

#### 4.7.1 4 种记忆类型

| 类型 | 用途 | 示例 |
|------|------|------|
| `user` | 用户是谁（角色、偏好、技能水平） | "用户是 Python 后端开发，喜欢 type hints" |
| `feedback` | 用户给出的纠正和指导 | "以后不要用 print 调试，用 logging" |
| `project` | 项目进展、目标、截止日期 | "正在迁移 auth 模块到 JWT，预计下周完成" |
| `reference` | 外部资源链接 | "API 文档: https://docs.example.com" |

#### 4.7.2 存储格式

```markdown
---
name: prefer-logging
description: 用户偏好使用 logging 而非 print
type: feedback
---

以后写代码时，用 logging 模块做调试输出，不要用 print()。
**Why:** 生产环境需要日志级别控制。
**How to apply:** 任何调试输出用 logging.debug()。
```

每份记忆一个 `.md` 文件，存储在 `~/.mini-claude/projects/<hash>/memory/`。

#### 4.7.3 语义召回（核心亮点）

```
用户输入 "帮我加个日志"
    │
    ▼
start_memory_prefetch()  ← 后台异步启动
    │
    ├── Gate 1: 输入必须是多词（跳过 "hello"）
    ├── Gate 2: 本会话召回量 < 60KB
    ├── Gate 3: 记忆目录有文件
    │
    ▼
scan_memory_headers()  ← 只读前 30 行的 frontmatter（快速扫描）
    │
    ▼
side_query()  ← 用一个小模型调用（不占用主对话上下文）
    │  提示词："以下哪些记忆与用户查询相关？"
    │  返回 JSON: {"selected_memories": ["prefer-logging.md", "project-auth.md"]}
    │
    ▼
format_memories_for_injection()  ← 格式化选中的记忆
    │
    ▼
注入到对话历史（作为 <system-reminder> 标签）
```

`MEMORY.md` 索引文件自动更新，列出所有记忆的快速索引。

---

### 4.8 `skills.py` — 技能系统

技能是可复用的提示词模板，存储在 `.claude/skills/<name>/SKILL.md`。

#### 4.8.1 技能文件格式

```markdown
---
name: commit
description: 生成约定式提交信息并提交
user-invocable: true
allowed-tools: [read_file, run_shell]
context: inline
---

你是一个提交信息生成器。分析当前 git diff 并...
```

#### 4.8.2 两种执行模式

| 模式 | `context: inline` | `context: fork` |
|------|-------------------|-----------------|
| 工作方式 | 提示词**注入到当前对话** | **新建一个子 Agent**，隔离执行 |
| 适用场景 | 小任务（生成消息、格式化） | 复杂任务（代码审查、全项目搜索） |
| 工具限制 | 无 | 按 `allowed-tools` 限制 |

#### 4.8.3 关键函数

| 函数 | 作用 |
|------|------|
| `discover_skills()` | 扫描 `~/.claude/skills/` 和 `.claude/skills/` 目录 |
| `get_skill_by_name(name)` | 按名称查找技能 |
| `resolve_skill_prompt(skill, args)` | 用参数替换模板变量（`$ARGUMENTS`, `${CLAUDE_SKILL_DIR}`） |
| `execute_skill(name, args)` | 返回 `{prompt, allowed_tools, context}` |
| `build_skill_descriptions()` | 生成系统提示词中的技能列表段落 |

**加载优先级**：项目级 skills 覆盖用户级同名 skills。

---

### 4.9 `subagent.py` — 子 Agent

主 Agent 可以派生子 Agent 执行独立任务。每个子 Agent 是全新的 Agent 实例（隔离的对话历史）。

#### 4.9.1 内置 Agent 类型

| 类型 | 工具 | 用途 |
|------|------|------|
| `explore` | read_file, list_files, grep_search | 代码库探索和搜索 |
| `plan` | read_file, list_files, grep_search | 只读分析 + 生成实施计划 |
| `general` | 全部工具（除 agent 自身） | 完整的独立任务执行 |

#### 4.9.2 自定义 Agent

在 `.claude/agents/<name>.md` 中定义：

```markdown
---
name: code-reviewer
description: 代码审查专家
allowed-tools: read_file, list_files, grep_search
---

你是一个资深代码审查者。审查以下代码的...
```

#### 4.9.3 关键函数

| 函数 | 作用 |
|------|------|
| `get_sub_agent_config(type)` | 返回 Agent 的系统提示词和工具列表 |
| `_discover_custom_agents()` | 扫描 `.claude/agents/` 目录 |
| `get_available_agent_types()` | 列出所有可用类型（内置 + 自定义） |
| `build_agent_descriptions()` | 生成系统提示词中的 Agent 描述段落 |

---

### 4.10 `tasks.py` — 任务追踪

让 Agent 能创建、追踪、更新复杂多步骤任务的进度。

#### 4.10.1 数据模型

```python
class TaskEntry:
    id: str          # 8位 UUID hex
    subject: str     # 任务标题
    description: str # 任务详情
    status: str      # pending | in_progress | completed | deleted
    created_at: str  # ISO 时间戳
    updated_at: str  # ISO 时间戳
```

#### 4.10.2 状态机

```
pending ──→ in_progress ──→ completed
  │                            │
  └──────── deleted ←──────────┘
```

#### 4.10.3 存储

每个任务一个 JSON 文件：`~/.mini-claude/projects/<cwd_hash>/tasks/<task_id>.json`

#### 4.10.4 关键函数

| 函数 | 作用 |
|------|------|
| `create_task(subject, description)` | 新建任务，状态设为 pending，返回 task_id |
| `list_tasks(include_deleted)` | 列出所有任务，默认过滤 deleted，按创建时间倒序 |
| `update_task(task_id, *, status, subject, description)` | 更新任务字段，返回是否成功 |

---

### 4.11 `mcp_client.py` — MCP 客户端

MCP（Model Context Protocol）是一种标准协议，让 LLM 可以连接外部工具服务器。

#### 4.11.1 架构

```
Agent
  └── McpManager   ← 管理所有 MCP 连接
       ├── McpConnection("filesystem")  ← stdio JSON-RPC 子进程
       ├── McpConnection("github")      ← stdio JSON-RPC 子进程
       └── McpConnection("database")    ← stdio JSON-RPC 子进程
```

#### 4.11.2 配置

从 `settings.json` 的 `mcpServers` 段读取：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"],
      "env": {}
    }
  }
}
```

#### 4.11.3 MCP 协议握手

```
Client (mini-claude)              Server (npx process)
    │                                    │
    │──── initialize ───────────────────►│  "你好，我支持 v2024-11-05"
    │◄─── capabilities ─────────────────│  "我能提供这些工具..."
    │──── initialized notification ────►│  "收到，开始工作"
    │                                    │
    │──── tools/list ───────────────────►│  "有哪些工具?"
    │◄─── [tool1, tool2, ...] ──────────│  "有 read, write, search..."
    │                                    │
    │──── tools/call("read", {...}) ────►│  "执行 read 工具"
    │◄─── result ───────────────────────│  "这是结果"
```

#### 4.11.4 关键类

| 类/函数 | 作用 |
|---------|------|
| `McpConnection` | 管理单个 MCP 服务器：启动子进程、JSON-RPC 通信、stdout 行读取循环 |
| `McpConnection.connect()` | 启动子进程（`asyncio.create_subprocess_exec`） |
| `McpConnection.initialize()` | MCP 协议握手（initialize → initialized 通知） |
| `McpConnection.list_tools()` | 获取服务器的工具列表 → 转成 Anthropic 工具定义格式 |
| `McpConnection.call_tool(name, args)` | 调用远程工具 |
| `McpManager` | 管理所有连接：加载配置 → 并行连接 → 收集工具 → 路由调用 |
| `McpManager.load_and_connect()` | 首次对话时延迟加载（`agent.py:325-333`） |

#### 4.11.5 工具命名

MCP 工具以 `mcp__服务器名__工具名` 命名，避免冲突。例如：`mcp__filesystem__read_file`。

---

### 4.12 `frontmatter.py` — 元数据解析

解析 YAML frontmatter（文件开头的 `---` 分隔的元数据块）：

```
---
name: my-skill
description: does something
type: user
---
这里是正文内容...
```

| 函数 | 作用 |
|------|------|
| `parse_frontmatter(content)` | 解析 `---...---` 块，返回 `FrontmatterResult(meta=dict, body=str)` |
| `format_frontmatter(meta, body)` | 反向操作：把 dict + body 格式化成 frontmatter 文件 |

被 `memory.py`（记忆文件）和 `skills.py`（技能文件）复用。

---

## 5. 数据流向图

```
┌──────────┐
│  用户输入  │
└────┬─────┘
     │ agent.chat(user_message)
     ▼
┌──────────────────────────────────────┐
│            Agent 核心循环             │
│                                      │
│  ┌──────────────────────────────┐    │
│  │ 1. 附加用户消息到对话历史      │    │
│  │ 2. 检查是否需要压缩           │    │
│  │ 3. 启动记忆预取（后台）        │    │
│  │ 4. 运行压缩管道 (Tier 1-3)   │    │
│  └──────────┬───────────────────┘    │
│             ▼                        │
│  ┌──────────────────────────────┐    │
│  │ 调用 LLM API                 │    │
│  │  ├─ Anthropic: stream +      │    │
│  │  │   content_block_stop 钩子  │    │
│  │  └─ OpenAI: stream +        │    │
│  │     tool_calls delta 组装     │    │
│  └──────────┬───────────────────┘    │
│             ▼                        │
│  ┌──────────────────────────┐        │
│  │ LLM 返回结果              │        │
│  │ ├─ 文本 → 流式打印        │        │
│  │ ├─ tool_use(s) → 执行     │        │
│  │ └─ usage → 累计 token     │        │
│  └──────────┬───────────────┘        │
│             ▼                        │
│  ┌──────────────────────────┐        │
│  │ 对每个 tool_use:          │        │
│  │  1. 权限检查              │        │
│  │  2. 需确认 → 弹出 (y/n)   │        │
│  │  3. 执行工具              │        │
│  │  4. 大结果 → 磁盘持久化    │        │
│  │  5. 结果附加到对话历史     │        │
│  └──────────┬───────────────┘        │
│             │                        │
│     有更多 tool_use?                 │
│     ├─ 是 → 回到步骤 2               │
│     └─ 否 → 本轮结束                  │
└──────────────────────────────────────┘
     │
     ▼
┌──────────┐
│ 打印结果  │
└──────────┘
```

---

## 6. 如何扩展

### 添加一个新工具（4 步）

以添加 `timer` 工具为例：

**步骤 1：`tools.py` — 添加工具定义**
```python
# 在 tool_definitions 列表中添加
{
    "name": "timer",
    "description": "Set a countdown timer. Returns when time is up.",
    "input_schema": {
        "type": "object",
        "properties": {
            "seconds": {"type": "number", "description": "Seconds to wait"},
        },
        "required": ["seconds"],
    },
},
```

**步骤 2：`tools.py` — 添加处理函数**
```python
def _timer(inp: dict) -> str:
    import time
    seconds = int(inp.get("seconds", 0))
    time.sleep(min(seconds, 60))  # 最多 60 秒
    return f"Timer done: {seconds}s elapsed"
```

**步骤 3：`tools.py` — 注册到 handlers dict**
```python
handlers = {
    ...
    "timer": _timer,
}
```

**步骤 4（可选）：根据类型加入权限组**
```python
# 如果只读
READ_TOOLS.add("timer")
# 如果可以并行
CONCURRENCY_SAFE_TOOLS.add("timer")
```

### 添加新的子 Agent 类型

在 `.claude/agents/` 下创建 `.md` 文件即可，无需改代码。

### 添加技能

在 `.claude/skills/<技能名>/` 下创建 `SKILL.md`，写 frontmatter + 提示词模板。

### 连接 MCP 服务器

在 `.claude/settings.json` 的 `mcpServers` 中添加配置即可，Agent 首次对话时自动连接。
