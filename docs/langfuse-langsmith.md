# Langfuse 与 LangSmith 工作原理

> 两者解决的是同一个问题——给 LLM 应用做可观测性——工作原理也高度相似,都是三层:`埋点 SDK 采集` → `异步批量上报` → `后端存储 + UI 展示`。区别主要在采集标准和部署形态。本文以本项目(deepagents 调研 agent)为背景说明。

## 一、共同原理:一次调用怎么变成一条 trace

以本项目为例,调用链是 `agent.invoke() → 多个 LLM 调用 → Tavily 工具调用`。无论 LangSmith 还是 Langfuse:

1. **插桩采集**:SDK 通过 LangChain 的 callback 机制拦截每次模型/工具调用,记录输入输出、token 数、耗时、元数据。
2. **组织成树**:每个调用是一个节点,按父子关系挂成树(根 = 整个 agent 运行)。子节点继承父节点的 `trace_id`、tags、metadata。
3. **异步传输**:SDK 先把事件序列化进内存队列,由后台线程**批量 POST** 到后端(所以短进程要手动 `flush()`,否则没上报就退出了)。
4. **后端加工**:校验 → 解析 → 存库。UI 再按树形把一次运行渲染成可回放的 trace。

## 二、LangSmith:闭源 SaaS,围绕 LangChain 生态

- **采集**:`@traceable` 装饰器或 LangChain 自带集成。Python 用 `contextvars` 在调用栈中自动传播"当前父节点",所以嵌套关系不用手动传。
- **数据结构**:核心是 **RunTree**,用 `trace_id` + `dotted_order` 一个字符串同时编码层级和时间——`dotted_order` 前缀匹配就能取出一棵子树,排序也天然按时间。
- **上报**:run 序列化后走 `/runs/multipart` 批量 POST,大字段(输入输出、附件)单独提取,支持压缩。
- **后端**:多服务架构——前端 Nginx(唯一入口) → backend 校验 → **queue 异步处理** → **ClickHouse**(存 trace 和分析) + PostgreSQL(用户/项目/数据集) + Redis(队列缓存)。
- **新动向**:自研了 **SmithDB**(Rust 写的对象存储 + LSM 树数据层),已接管美区云 100% 的采集与查询流量。也支持接收标准 OTLP 上报。
- 默认是闭源 SaaS;**企业版才可自托管**。

## 三、Langfuse:开源自托管,以 OpenTelemetry 为标准

- **采集**:自家 Python/JS SDK **底层就是 OpenTelemetry**,对 LangChain 等 20+ 框架提供集成。也开放**标准 OTLP 端点**(`/api/public/otel/v1/traces`),任何能发 OTLP 的工具都能直接接入。
- **数据结构**:`trace → observations`(span / generation / event / tool / agent…),支持 session 分组、用户、tags。
- **上报**:SDK 把 OTel spans 批量导出到后端(或 ingestion API / OTLP 端点)。
- **后端是"接收与处理解耦"的两段式**:

  1. **Web 层**只做接收和持久化——校验事件、按实体分组排序、把**原始事件完整写入 S3**(按项目/时间分目录),然后只把 S3 文件 key 放进 Redis 队列。
  2. **Worker 层**从 S3 下载、富化:解析 prompt 引用、匹配模型定价表算成本、把嵌套 metadata 扁平化、归一化时间戳,最后写 **ClickHouse**。

- 存储:ClickHouse(观测数据,OLAP 列存) + PostgreSQL(用户/项目/prompt) + Redis(队列) + S3(原始事件/附件)。从 Postgres 迁到 ClickHouse 就是因为列存做 GROUP BY 聚合快几十到上百倍。

## 四、核心差异对比

| 维度 | LangSmith | Langfuse |
|---|---|---|
| 开源/部署 | 闭源 SaaS(企业版可自托管) | 开源,可自由自托管 |
| 采集标准 | 自家协议为主,兼容 OTLP | 以 OTel 为标准 |
| 集成面 | 与 LangChain 生态绑定最深 | 20+ 框架通用 |
| 数据模型 | RunTree(run 树) | trace → observations 树 |
| 后端架构 | 多服务 + ClickHouse + SmithDB | Web/Worker 解耦 + S3 + ClickHouse |
| 特色 | 数据集 + 在线评测一体 | OTel 生态、prompt 管理、评估 |

## 五、对应到本项目

正因为两者都挂在 LangChain 的 callback 上,所以本项目的"LangSmith / Langfuse 二选一"才能在代码层面无缝切换——生成的其实是同一棵调用树,只是 LangSmith 管它叫 run,Langfuse 管它叫 observation,上报到的后端不同而已。

接入细节见 `src/quickstart/main.py` 中的链路追踪逻辑。

## 六、把 Langfuse 接入 Claude Code 与 Codex

除了给应用代码埋点,Langfuse 官方还支持直接追踪 AI 编程工具本身(Claude Code、Codex 等),两者都走各自的 hooks 机制,无需代理/网关。接入后,你使用这些工具时的**会话、模型调用、工具执行、token 成本**都会进入 Langfuse,与应用的 SDK 追踪落在同一个项目里,只是来源不同。

### 6.1 Claude Code

原理:Claude Code 提供 [hooks 系统](https://code.claude.com/docs/en/hooks-guide),接入方式是用 **Stop hook**——每次 Claude Code 回复后读取会话 transcript,转成 Langfuse trace,同一会话用 `session_id` 分组。追踪按项目通过 `.claude/settings.json` 中的环境变量**逐项目开启**。

**方式一(推荐):插件市场安装**

```bash
claude plugin marketplace add langfuse/Claude-Observability-Plugin
claude plugin install langfuse-observability@langfuse-observability
```

重启后按提示填写三个变量:

- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_BASE_URL`(本机自托管填 `http://localhost:3000`)

要求:Python 3.9+ 且 `pip install "langfuse>=4.0,<5"`。

**方式二(手动):Stop hook 脚本**

1. 把官方脚本放到 `~/.claude/hooks/langfuse_hook.py`(脚本从 [Langfuse Claude Code 文档](https://langfuse.com/integrations/developer-tools/claude-code) 获取)。
2. 在项目的 `.claude/settings.json` 注册 Stop hook,并注入 `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_BASE_URL` 三个环境变量。

两种方式都能追踪:用户输入、助手回复与推理、工具调用及其输入输出、会话分组、耗时。

### 6.2 OpenAI Codex

要求:Node.js 22+、Codex 0.128+。

原理:通过 Codex 的 **plugin hooks(Stop hook,每个 turn 后执行)** 读取 Codex 的会话 transcript(rollout 文件),重建 turn 并用 Langfuse TypeScript SDK 上报;同一会话用 `session_id` 分组;sidecar 文件记录已上传的 turn,避免重复。追踪通过 `TRACE_TO_LANGFUSE=true` 显式开启,fail-open(出错只记录不阻塞会话)。

**步骤**:

```bash
# 1. 添加插件市场
codex plugin marketplace add langfuse/codex-observability-plugin

# 2. 安装追踪插件
codex plugin add tracing@codex-observability-plugin
```

```toml
# 3. 在 ~/.codex/config.toml(全局)或 <project>/.codex/config.toml(项目级)开启
[features]
plugin_hooks = true

[plugins."tracing@codex-observability-plugin"]
enabled = true
```

首次运行插件 hook 时,Codex 可能请求授权 Stop hook,选择允许。

**配置凭据**(二选一):

- 环境变量(加入 `~/.zshrc`):

  ```bash
  export TRACE_TO_LANGFUSE="true"
  export LANGFUSE_PUBLIC_KEY="pk-lf-..."
  export LANGFUSE_SECRET_KEY="sk-lf-..."
  export LANGFUSE_BASE_URL="http://localhost:3000"  # 本机自托管;Cloud 填区域地址
  ```

- 配置文件 `~/.codex/langfuse.json`(全局)或 `<project>/.codex/langfuse.json`(项目级):

  ```json
  {
    "enabled": true,
    "public_key": "pk-lf-...",
    "secret_key": "sk-lf-...",
    "base_url": "http://localhost:3000"
  }
  ```

配置解析优先级:默认值 → 全局配置 → 项目配置 → 环境变量(环境变量最高)。`LANGFUSE_CODEX_*` 前缀的变量可覆盖标准 `LANGFUSE_*` 变量,把凭据限定到 Codex。

**验证**:完全重启 Codex 后新开会话,连发两条消息即可看到上报。Langfuse 中按 `Codex Turn` 搜索:每个 turn 一条 trace(agent 观测),每个模型响应一条 generation(含 token 用量),工具调用(`exec_command`、`apply_patch`、`spawn_agent`…)嵌套在其下,subagent 嵌套在触发的 turn 下,同会话在 Sessions 页可回放。

### 6.3 与本项目的关系

本项目 agent 的追踪是 **SDK 代码埋点**(`src/quickstart/main.py`),Claude Code / Codex 的追踪是 **hooks 埋点**——两者是独立的追踪来源,但都汇入同一个 Langfuse 项目,可统一按应用/工具/开发者筛选与核算成本。

## 参考资料

- [LangSmith 架构](https://docs.langchain.com/langsmith/engine-self-hosted)
- [LangSmith SDK 系统架构](https://deepwiki.com/langchain-ai/langsmith-sdk/1.2-system-architecture)
- [Introducing SmithDB](https://web.archive.org/web/20260609081445/https://www.langchain.com/blog/introducing-smithdb)
- [Langfuse 平台架构](https://js-sdk-v4-docs-snapshot.langfuse.com/handbook/product-engineering/architecture/)
- [Langfuse 数据摄入管道](https://deepwiki.com/langfuse/langfuse/6-data-ingestion-pipeline)
- [Tracing coding agents: Claude Code, Codex, Copilot & more - Langfuse](https://langfuse.com/resources/engineering/coding-agent-tracing)
- [Claude Code Tracing with Langfuse](https://langfuse.com/integrations/developer-tools/claude-code)
- [OpenAI Codex tracing with Langfuse](https://langfuse.com/integrations/developer-tools/codex)
