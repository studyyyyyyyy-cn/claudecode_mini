# claude_code_mini — Python 版 Mini Claude Code

与 Claude Code 架构镜像的 Python 实现。**需要 Python >= 3.11**。

> GitHub: [studyyyyyyyy-cn/claudecode_mini](https://github.com/studyyyyyyyy-cn/claudecode_mini)

## 快速开始

```bash
# 安装（需要 Python 3.11+）
pip install -e .

# 设置 API Key
export ANTHROPIC_API_KEY=sk-ant-...

# 运行
mini-claude-py "hello"               # 一次性模式
mini-claude-py                       # 交互式 REPL
mini-claude-py --yolo "list files"   # 跳过确认
mini-claude-py --plan "refactor this" # 计划模式
python -m mini_claude "hello"        # 也可以用 python -m 方式运行

# 使用 OpenAI 兼容后端
OPENAI_API_KEY=sk-xxx mini-claude-py --api-base https://aihubmix.com/v1 --model deepseek-v4-flash "hello"
```

## 文件结构

| 文件 | 说明 |
|------|------|
| `agent.py` | Agent 核心循环：双后端（Anthropic + OpenAI）、流式、4 层压缩、计划模式、子 Agent、预算控制 |
| `tools.py` | 13 个工具 + 5 种权限模式（read/write/edit/list/grep/shell/skill/web/agent/plan/task） |
| `__main__.py` | CLI 入口与交互式 REPL |
| `ui.py` | 终端 UI（基于 rich） |
| `prompt.py` | 系统提示词构造，支持 CLAUDE.md / rules / skills 上下文注入 |
| `session.py` | 会话持久化（JSON） |
| `memory.py` | 4 类型文件记忆系统 + 语义召回 |
| `skills.py` | 技能系统（SKILL.md frontmatter + inline/fork 模式） |
| `subagent.py` | 子 Agent 系统（explore / plan / general + 自定义 Agent） |
| `frontmatter.py` | YAML frontmatter 解析器 |
| `mcp_client.py` | MCP 客户端（stdio JSON-RPC，支持多服务器） |
| `tasks.py` | **NEW** 任务追踪系统（创建 / 列表 / 更新） |

## 依赖

- `anthropic` — Anthropic SDK（流式）
- `openai` — OpenAI SDK（兼容后端）
- `rich` — 终端彩色输出

---

## 新功能：任务追踪系统

Agent 可以通过 3 个工具管理复杂多步骤任务的进度。

### 工具

| 工具 | 参数 | 说明 |
|------|------|------|
| `task_create` | `subject` (必填), `description` (可选) | 创建新任务，返回 8 位 task_id |
| `task_list` | 无 | 列出所有未删除任务，按状态排序 |
| `task_update` | `task_id` (必填), `status`/`subject`/`description` (可选) | 更新任务状态或详情 |

### 状态机

```
pending ──→ in_progress ──→ completed
  │                            │
  └──────── deleted ←──────────┘
```

- **pending** — 待开始
- **in_progress** — 进行中（Agent 开始工作时标记）
- **completed** — 已完成
- **deleted** — 废弃（不再显示在列表中）

### 存储

JSON 文件存储在 `~/.mini-claude/projects/<cwd_hash>/tasks/<task_id>.json`，按项目隔离。

```json
{
  "id": "6f0adb9a",
  "subject": "重构 agent.py",
  "description": "拆分大函数，提取公共逻辑",
  "status": "in_progress",
  "created_at": "2026-06-16T13:36:38Z",
  "updated_at": "2026-06-16T13:36:38Z"
}
```

### 使用示例

```
> 帮我创建一个任务：重构 agent.py，拆分大函数
  📋 task_create 重构 agent.py
  Task created: [6f0adb9a] 重构 agent.py

> 再来一个：写单元测试
  📋 task_create 写单元测试
  Task created: [e495d029] 写单元测试

> 列出所有任务
  🔍 task_list
  2 tasks:
    [e495d029] ○ 写单元测试
    [6f0adb9a] ○ 重构 agent.py

> 我开始做第一个了，标记一下
  🔧 task_update task_id=6f0adb9a status=in_progress
  Task [6f0adb9a] updated: status=in_progress
```

### REPL 命令

| 命令 | 说明 |
|------|------|
| `/clear` | 清除对话历史 |
| `/plan` | 切换计划模式 |
| `/cost` | 查看 token 用量和费用 |
| `/compact` | 手动压缩对话上下文 |
| `/memory` | 列出已保存的记忆 |
| `/skills` | 列出可用技能 |
| `/<skill-name>` | 调用技能 |

### 权限模式

| 模式 | CLI 参数 | 说明 |
|------|----------|------|
| `default` | (默认) | 危险命令和新建文件需确认 |
| `plan` | `--plan` | 只读，仅可编辑计划文件 |
| `acceptEdits` | `--accept-edits` | 自动批准文件编辑，危险 shell 仍确认 |
| `dontAsk` | `--dont-ask` | 自动拒绝需确认的操作（CI 模式） |
| `bypassPermissions` | `--yolo` | 跳过所有确认 |

### OpenAI 兼容后端

支持任意 OpenAI 兼容 API（DeepSeek、AIHubMix 等）：

```bash
OPENAI_API_KEY=sk-xxx mini-claude-py --api-base https://api.deepseek.com --model deepseek-v4-flash "hello"
```

或设置环境变量：

```bash
export OPENAI_API_KEY=sk-xxx
export OPENAI_BASE_URL=https://api.deepseek.com
export OPENAI_MODEL=deepseek-v4-flash
mini-claude-py "hello"
```

### 高级选项

| 参数 | 说明 |
|------|------|
| `--thinking` | 启用扩展思考（Anthropic 模型） |
| `--max-cost USD` | 费用上限（估算），超出后停止 |
| `--max-turns N` | 最大对话轮数上限 |
| `--resume` | 恢复上一个会话 |
