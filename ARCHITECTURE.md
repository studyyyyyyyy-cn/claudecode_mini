# claude_code_mini 技术深度解析

## 一、架构设计

### 1.1 整体模式：ReAct Agent

项目采用经典的 **ReAct (Reasoning + Acting)** 模式。Agent 本身不执行任务，它充当 LLM 的"手和眼"——LLM 负责思考决策，Agent 负责执行 LLM 指令并反馈结果。

```
┌──────────────────────────────────────────────────┐
│                  Agent 主循环                     │
│                                                  │
│  用户输入 ──► 消息队列 ──► LLM API               │
│                 ▲            │                   │
│                 │       返回 text │ tool_calls    │
│                 │            │        │          │
│                 │      打印到终端    ▼            │
│                 │           权限检查 → 执行工具    │
│                 └──────── 结果注入 ◄─────────────  │
└──────────────────────────────────────────────────┘
```

### 1.2 模块分层

```
┌─────────────────────────────────────────┐
│              __main__.py                │  入口层：CLI 解析、REPL 循环
├─────────────────────────────────────────┤
│              agent.py                   │  核心层：Agent 循环、LLM 调用
│          ┌──────┼──────┐               │
│     Anthropic   OpenAI  MCP            │  双后端 + 协议扩展
├─────────────────────────────────────────┤
│  tools.py │ prompt.py │ session.py     │  设施层
│  memory.py│ skills.py │ subagent.py    │
│  tasks.py │ mcp_client.py │ ui.py     │
├─────────────────────────────────────────┤
│         ~/.mini-claude/                 │  持久层：会话、记忆、任务均落盘
└─────────────────────────────────────────┘
```

### 1.3 双后端设计

一套 Agent 逻辑，两个 LLM 协议适配：

| 维度 | Anthropic 后端 | OpenAI 兼容后端 |
|------|---------------|----------------|
| SDK | `anthropic.AsyncAnthropic` | `openai.AsyncOpenAI` |
| 协议 | `/v1/messages` | `/v1/chat/completions` |
| 工具格式 | 原生 `tools` 数组 | 转译为 `function` 类型 |
| 历史格式 | `role + content list` | `role + content string` |
| 流式工具 | `content_block_stop` 事件 → 立即执行 | delta 组装完整后批量执行 |
| 思考模式 | 支持 extended thinking | ❌ |

切换方式：检测 `OPENAI_BASE_URL` 或 `--api-base` 参数，内部用 `use_openai` 布尔值分流所有逻辑。

### 1.4 工具系统

13 个工具，按副作用分级：

```
        无副作用（可并行）              有副作用（串行）
    ┌──────────────────────┐    ┌──────────────────────┐
    │ read_file            │    │ write_file            │
    │ list_files           │    │ edit_file             │
    │ grep_search          │    │ run_shell             │
    │ web_fetch            │    │ task_create           │
    │ task_list            │    │ task_update           │
    │ tool_search          │    │ agent (子Agent)       │
    └──────────────────────┘    │ skill                 │
      CONCURRENCY_SAFE_TOOLS    │ enter/exit_plan_mode  │
                                └──────────────────────┘
```

工具通过 `handlers dict` 注册，新增工具只需 3 步：添加定义 → 实现函数 → 注册到 dict。

### 1.5 子 Agent 机制

采用 **Fork-Return** 模式：

```
主 Agent                  子 Agent (全新实例，隔离上下文)
   │                            │
   │── agent(type="explore")──►│
   │                            │── 独立搜索、读文件
   │                            │── 不污染主对话历史
   │◄─── return {text, tokens} ─│
   │
   │ 合并 tokens 计数，打印结果
```

三种内置类型：`explore`（只读搜索）、`plan`（只读规划）、`general`（完整工具集）。用户可通过 `.claude/agents/*.md` 自定义类型。

---

## 二、上下文管理

### 2.1 问题：LLM 上下文窗口有限

模型一次最多处理 200K tokens。对话越长，历史消息越多，最终会超过窗口上限导致请求失败。需要在"保留关键信息"和"控制上下文大小"之间平衡。

### 2.2 5 层压缩管道

每轮 LLM 调用前执行，分层递进：

```
上下文利用率
    │
 0% ├── 正常运行，不触发任何压缩
    │
50% ├── Tier 1: _budget_tool_results()
    │    超大工具结果（>15KB）→ 保留头尾，中间截断
    │    15000 字符预算（高负载）/ 30000（低负载）
    │
60% ├── Tier 2: _snip_stale_results()
    │    旧的搜索/读文件结果 → 替换为 "[Content snipped - re-read if needed]"
    │    保留最近 3 个结果，同文件多次读取只保留最新
    │
    ├── Tier 3: _microcompact()
    │    距上次 API 调用超过 5 分钟 → 更激进地清除旧结果
    │    替换为 "[Old result cleared]"
    │
85% ├── Tier 4: _compact_conversation()
    │    调用 LLM 把整个对话总结为一段话
    │    对话历史被重建为: [摘要] + [确认] + [当前用户消息]
    │    这是"核选项"，代价是丢失细节
    │
    └── Tier 0: _persist_large_result() (每次工具执行后)
         单个结果 > 30KB → 写磁盘，上下文中只保留 200 行预览 + 文件路径
         LLM 可通过 read_file 重新读取完整内容
```

### 2.3 压缩算法细节

**Tier 1 预算裁剪**：
```
原始: [前1000行 ... 中间8000行 ... 后1000行]
裁剪: [前250行 ... ...budgeted: 8000 chars truncated... ... 后250行]
```

**Tier 2 旧结果替换**：
- 找所有 SNIPPABLE_TOOLS（read_file, grep_search, list_files, run_shell, web_search）的结果
- 同一文件的多次读取 → 只保留最后一次
- 超过 KEEP_RECENT_RESULTS(3) 个结果的 → 最旧的标记为 `[Content snipped]`

**Tier 4 完全压缩**：
```
压缩前: [20轮对话, 5万tokens]
    │
    ▼ LLM 摘要
摘要: "用户要求重构 agent.py，已拆分了 chat 方法为 chat + _execute_tool_loop。
      当前正在添加错误处理。关键文件: agent.py:350, tools.py:640"

重建后:
  [系统提示词]
  user: [摘要]
  assistant: "明白了，继续。"
  user: "再加个日志"
```

### 2.4 Read-before-Edit 保证

Agent 在写/编辑文件前**必须**先读过该文件：

```python
# tools.py:654-662
if name in ("write_file", "edit_file"):
    if abs_path not in read_file_state:
        return "Error: 请先用 read_file 读取该文件"
    if os.path.getmtime(abs_path) != read_file_state[abs_path]:
        return "Warning: 文件已被外部修改，请重新读取"
```

`read_file_state` 是一个 dict：`{绝对路径 → 读取时的 mtime}`。如果 mtime 变了（文件被外部编辑器修改），Agent 会拒绝编辑并要求重读。

---

## 三、记忆机制

### 3.1 设计目标

让 Agent 在**跨会话**之间记住用户偏好、项目背景、关键决策——而不只是当前对话上下文。

### 3.2 存储模型

```
~/.mini-claude/projects/<cwd_hash>/
├── memory/
│   ├── MEMORY.md                  ← 自动生成的索引文件
│   ├── user_prefer-logging.md     ← 记忆文件
│   ├── feedback_no-print-debug.md
│   ├── project_auth-migration.md
│   └── reference_api-docs-url.md
└── tasks/
    ├── 6f0adb9a.json
    └── e495d029.json
```

每份记忆 = Markdown 文件 + YAML frontmatter：

```markdown
---
name: prefer-logging        ← 唯一标识
description: 用户偏好 logging 而非 print   ← 用于语义匹配
type: feedback              ← user | feedback | project | reference
---

记忆正文。对于 feedback 类型，需包含：
**Why:** 为什么要这样做
**How to apply:** 何时应用此规则
```

### 3.3 语义召回流程

这是最核心的创新——Agent 不加载全部记忆，而是**按需智能检索**：

```
用户输入: "帮我加个日志模块"
    │
    ▼
start_memory_prefetch()  ── 后台异步启动，不阻塞主流程
    │
    ├── Gate 1: 单字输入跳过（"hello"、"exit"）
    ├── Gate 2: 本会话累计注入 > 60KB → 停止召回
    └── Gate 3: 记忆目录无文件 → 跳过
    │
    ▼
scan_memory_headers()  ── 只读每个文件的前 30 行（frontmatter）
    构建清单: "- [feedback] prefer-logging (2026-06-15): 用户偏好..."
    │
    ▼
side_query()  ── 独立 API 调用（不占用主对话上下文）
    System: "从以下记忆中选择与用户查询相关的..."
    User: "查询: 加个日志模块\n\n可用记忆:\n- [feedback] prefer-logging..."
    │
    ▼
LLM 返回 JSON: {"selected_memories": ["prefer-logging.md"]}
    │
    ▼
format_memories_for_injection()
    包裹为 <system-reminder> 注入到对话历史
    │
    ▼
<system-reminder>
Memory (saved today): ~/.mini-claude/.../prefer-logging.md:
用户偏好使用 logging 模块而非 print()...
</system-reminder>
```

### 3.4 时效性检查

```python
def memory_freshness_warning(mtime_ms):
    days = (now - mtime) / 86400000
    if days > 1:
        return "此记忆是 N 天前的。请验证当前代码后使用。"
```

超过 1 天的记忆会附带时效警告，提醒 LLM 这是"过去的状态"。

### 3.5 MEMORY.md 自动索引

每次写入记忆文件时自动更新：

```markdown
# Memory Index
- [prefer-logging](user_prefer-logging.md) (feedback) — 用户偏好 logging 而非 print
- [auth-migration](project_auth-migration.md) (project) — JWT 迁移，预计下周完成
```

索引内容会注入到系统提示词，让 LLM 在**对话开始时**就知道有哪些记忆。

---

## 四、安全与权限

### 4.1 5 级权限模式

```
bypassPermissions ── 全部放行（--yolo）
    │
acceptEdits ── 编辑自动接受，危险命令仍需确认（--accept-edits）
    │
default ── 危险命令 + 新建文件需确认（默认）
    │
dontAsk ── 需确认的操作自动拒绝（--dont-ask，CI 模式）
    │
plan ── 全只读，仅允许编辑指定的计划文件（--plan）
```

### 4.2 权限检查决策树

```
check_permission(tool_name, input, mode)
    │
    ├── mode == bypassPermissions? ──────────────► ALLOW
    │
    ├── 命中 settings.json deny 规则? ──────────► DENY
    ├── 命中 settings.json allow 规则? ──────────► ALLOW
    │
    ├── tool in READ_TOOLS? ─────────────────────► ALLOW
    │   {read_file, list_files, grep_search, web_fetch, task_list}
    │
    ├── mode == plan?
    │   ├── tool in EDIT_TOOLS + 文件 = 计划文件? ─► ALLOW
    │   ├── tool in EDIT_TOOLS + 文件 ≠ 计划文件? ─► DENY
    │   └── tool == run_shell? ─────────────────────► DENY
    │
    ├── mode == acceptEdits + tool in EDIT_TOOLS?─► ALLOW
    │
    ├── 触发确认条件?
    │   ├── run_shell + 危险命令模式匹配 ──────────► CONFIRM
    │   ├── write_file + 文件已存在 ───────────────► ALLOW
    │   ├── write_file + 文件不存在 ───────────────► CONFIRM
    │   └── edit_file + 文件不存在 ────────────────► CONFIRM
    │
    └── 以上均不命中 ──────────────────────────────► ALLOW
```

### 4.3 危险命令检测

18 个正则模式覆盖常见危险操作：

```python
DANGEROUS_PATTERNS = [
    r"\brm\s",                    # rm -rf ...
    r"\bgit\s+(push|reset|clean|checkout\s+\.)",  # git push/reset/clean
    r"\bsudo\b",                  # sudo ...
    r"\bmkfs\b",                  # mkfs 格式化
    r"\bdd\s",                    # dd 磁盘操作
    r">\s*/dev/",                 # 写入设备文件
    r"\bkill\b", r"\bpkill\b",   # 杀进程
    r"\breboot\b", r"\bshutdown\b",  # 重启/关机
    r"\bdel\s", r"\brmdir\s",    # Windows 删除
    r"\bformat\s",               # Windows 格式化
    r"\btaskkill\s",             # Windows 杀进程
    r"\bRemove-Item\s",          # PowerShell 删除
    r"\bStop-Process\s",         # PowerShell 杀进程
]
```

匹配到任何模式 → 弹出 `⚠ Dangerous command: xxx` 让用户确认 (y/n)。

### 4.4 配置文件权限规则

来自 `~/.claude/settings.json` 和 `.claude/settings.json`（项目级覆盖用户级）：

```json
{
  "permissions": {
    "allow": [
      "run_shell(npm test)",      // 允许 npm test
      "run_shell(git diff *)",    // 允许 git diff 任何参数
      "read_file(*)"              // 允许读取所有文件
    ],
    "deny": [
      "run_shell(rm *)",          // 禁止所有 rm 命令
      "write_file(/etc/*)",       // 禁止写入 /etc/
      "edit_file(*.env)"          // 禁止编辑 .env 文件
    ]
  }
}
```

规则匹配逻辑：`工具名(匹配模式)`，`*` 通配符做前缀匹配。

### 4.5 计划模式隔离

Plan 模式是一种特殊的"安全沙箱"：

```
进入 plan 模式:
  ├── 系统提示词注入 Plan Mode 指令
  ├── 生成计划文件路径: ~/.claude/plans/plan-{session_id}.md
  ├── LLM 被限制: 只能读文件 + 编辑计划文件
  └── 所有其他写入操作 → 自动拒绝

退出 plan 模式:
  ├── 展示计划内容给用户
  ├── 4 个选项:
  │   1. 清空上下文 + 执行 (全新开始，自动接受编辑)
  │   2. 保留上下文 + 执行 (保留分析上下文)
  │   3. 手动确认每个编辑 (最安全)
  │   4. 继续修改计划
  └── 按用户选择恢复权限模式
```

### 4.6 API Key 安全

- API Key **只从环境变量读取**，永不写入任何文件或对话历史
- `.claude/` 目录（含 `settings.local.json`）已加入 `.gitignore`，防止本地配置泄露
- 子 Agent 继承主 Agent 的客户端配置，不需要重复传递密钥

---

## 总结：四个系统的协作

```
          安全权限（每个工具调用前）
               │
               ▼
用户输入 ──► Agent 循环 ◄── 上下文管理（防止爆窗口）
               │
               ▼
          记忆机制（注入相关历史偏好）
               │
               ▼
          LLM API 调用
               │
               ▼
         执行工具 → 返回结果 → 循环
```

- **架构设计**决定了 Agent "能做什么"
- **上下文管理**决定了 Agent "能做多久"
- **记忆机制**决定了 Agent "能记住什么"
- **安全权限**决定了 Agent "不能做什么"
