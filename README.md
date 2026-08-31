# Quickstart · 深度调研 Agent

基于 [deepagents](https://github.com/langchain-ai/deepagents) 的联网调研 Agent:给定一个问题,由 LLM 调用 Tavily 联网搜索,最终生成一份结构化的 markdown 调研报告。

## 功能特性

- **联网调研**:通过 Tavily 搜索获取实时信息
- **结构化报告**:LLM 汇总为 markdown 文档
- **自定义问题**:通过命令行参数指定调研主题
- **报告落盘**:自动保存到 `outputs/`,也可用 `-o` 指定保存路径

## 环境要求

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) 包管理器

## 安装

```bash
uv sync
```

## 配置

在项目根目录创建 `.env` 文件(参考 `.env.example`,两种写法 `KEY=value` 或 `export KEY="value"` 都支持):

```
TAVILY_API_KEY=your_tavily_key
DEEPSEEK_API_KEY=your_deepseek_key

# 可选:LangSmith 链路追踪
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
```

| 变量 | 必填 | 说明 |
|---|---|---|
| `TAVILY_API_KEY` | 是 | [Tavily](https://tavily.com) 联网搜索 API 密钥 |
| `DEEPSEEK_API_KEY` | 是 | [DeepSeek](https://platform.deepseek.com) 模型 API 密钥 |
| `LANGCHAIN_TRACING_V2` | 否 | 开启 LangSmith 追踪 |
| `LANGCHAIN_API_KEY` | 否 | LangSmith API 密钥,配合追踪使用 |

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
