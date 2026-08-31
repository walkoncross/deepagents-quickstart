# Quickstart · 深度调研 Agent

基于 [deepagents](https://github.com/langchain-ai/deepagents) 的联网调研 Agent:给定一个问题,由 LLM 调用 Tavily 联网搜索,最终生成一份结构化的 markdown 调研报告。

## 功能特性

- **联网调研**:通过 Tavily 搜索获取实时信息
- **结构化报告**:LLM 汇总为 markdown 文档
- **自定义问题**:通过命令行参数指定调研主题
- **报告落盘**:自动保存到 `outputs/`,也可用 `-o` 指定保存路径
- **链路追踪**:LangSmith / Langfuse 二选一,自动采集模型调用、token 用量、工具搜索等完整链路

## 环境要求

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) 包管理器

## 安装

```bash
# 基础安装(仅支持 LangSmith 追踪,无需额外依赖)
uv sync

# 启用 Langfuse 追踪时,追加安装 langfuse 依赖
uv sync --extra langfuse
```

## 配置

在项目根目录创建 `.env` 文件(参考 `.env.example`,两种写法 `KEY=value` 或 `export KEY="value"` 都支持)。

链路追踪二选一,配置任意一套即可:

```
TAVILY_API_KEY=your_tavily_key
DEEPSEEK_API_KEY=your_deepseek_key

# 方案 A:LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key

# 方案 B:Langfuse(与方案 A 二选一;两套都配置时优先 Langfuse)
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_BASE_URL=http://localhost:3000
```

| 变量 | 必填 | 说明 |
|---|---|---|
| `TAVILY_API_KEY` | 是 | [Tavily](https://tavily.com) 联网搜索 API 密钥 |
| `DEEPSEEK_API_KEY` | 是 | [DeepSeek](https://platform.deepseek.com) 模型 API 密钥 |
| `LANGCHAIN_TRACING_V2` | 否 | 开启 LangSmith 追踪 |
| `LANGCHAIN_API_KEY` | 否 | LangSmith API 密钥,配合追踪使用 |
| `LANGFUSE_SECRET_KEY` | 否 | Langfuse 密钥,启用 Langfuse 追踪(需 `--extra langfuse` 安装) |
| `LANGFUSE_PUBLIC_KEY` | 否 | Langfuse 公钥,配合追踪使用 |
| `LANGFUSE_BASE_URL` | 否 | Langfuse 服务地址,默认 `http://localhost:3000`(本地自托管) |

Langfuse 密钥在项目设置 → API Keys 中创建;没有账号可免费注册 [Langfuse Cloud](https://langfuse.com/cloud) 或本地自托管。

## 使用方法

```bash
# 使用默认问题调研
uv run quickstart

# 指定调研问题
uv run quickstart "LangGraph 和 CrewAI 的区别"

# 指定报告保存路径(父目录不存在会自动创建)
uv run quickstart "..." -o docs/report.md
uv run quickstart "..." --output my_report.md
```

| 参数 | 说明 |
|---|---|
| `query`(位置参数) | 调研问题,默认 `What is langgraph?` |
| `-o, --output PATH` | 报告保存路径,默认自动保存到 `outputs/时间戳_问题片段.md` |

## 链路追踪(LangSmith / Langfuse 二选一)

程序自动判断追踪后端:

- 配置了 `LANGFUSE_PUBLIC_KEY` 与 `LANGFUSE_SECRET_KEY` → **Langfuse** 追踪(同时自动关闭 LangSmith,避免重复上报)
- 否则 → **LangSmith** 追踪(依赖 `LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY`)

两种后端都会自动记录:

- **模型调用**:DeepSeek 模型名、输入/输出 token 与预估成本
- **工具调用**:Tavily 联网搜索的参数与返回
- **推理步骤**:agent 的规划、反思等中间过程

使用 Langfuse 时,每次运行生成一条 `deep-research-agent` trace,附带 `tags=["deep-research", "agent"]` 与 `metadata`(含调研问题与模型),可在 Langfuse UI 的 **Traces** 视图按名称或标签筛选。未安装 `langfuse` 依赖时程序自动回退 LangSmith,均不配置则正常运行但不产生 trace。

## 项目结构

```
quickstart/
├── src/quickstart/
│   ├── __init__.py      # 包入口,导出 main
│   ├── __main__.py      # 支持 python -m quickstart
│   ├── main.py          # CLI 入口 + agent 组装
│   ├── tools.py         # Tavily 搜索工具
│   ├── prompts.py       # 系统提示词
│   └── report.py        # 报告保存(文件名清洗 + 落盘)
├── outputs/             # 自动生成的调研报告(已 gitignore)
├── .env                 # 密钥配置(已 gitignore,不入库)
├── .env.example         # 密钥模板
├── .claude/skills/langfuse/  # Langfuse AI 技能(供 Claude Code 使用)
├── pyproject.toml
└── uv.lock
```

## 配置模型

默认模型为 `deepseek:deepseek-v4-flash`,修改 `src/quickstart/main.py` 中的 `MODEL` 常量即可,例如:

```python
MODEL = "openai:gpt-5.5"  # 需配置对应 API 密钥
```

## 常见问题

- **运行报错 `ModuleNotFoundError`**:先执行 `uv sync` 确保依赖齐全
- **报错提示缺少 API Key**:确认 `.env` 存在且在项目根目录(程序只从那里读取)
- **想用其他模型**:按上文修改 `MODEL`,并确保安装了对应的 langchain 集成包(如 DeepSeek 需要 `langchain-deepseek`)
