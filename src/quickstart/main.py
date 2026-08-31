"""CLI 入口:组装 research agent 并运行。"""
import argparse
import os

from dotenv import load_dotenv

# 必须在导入 Langfuse 之前加载环境变量,否则会以缺失/错误的凭据初始化客户端
load_dotenv()

from deepagents import create_deep_agent  # noqa: E402

from quickstart.prompts import research_instructions  # noqa: E402
from quickstart.report import save_report  # noqa: E402
from quickstart.tools import internet_search  # noqa: E402

# Langfuse 为可选依赖(见 pyproject.toml 的 [project.optional-dependencies] langfuse):
# 未安装时自动回退到 LangSmith,不阻塞程序运行
try:
    from langfuse import get_client, propagate_attributes  # noqa: E402
    from langfuse.langchain import CallbackHandler  # noqa: E402
except ImportError:
    pass

DEFAULT_QUERY = "What is langgraph?"
MODEL = "deepseek:deepseek-v4-flash"  # 可换 openai:gpt-5.5
# 实际使用的模型名(去掉 provider 前缀,如 "deepseek:deepseek-v4-flash" → "deepseek-v4-flash"),
# 供 Langfuse 按模型统计与成本核算
MODEL_NAME = MODEL.split(":", 1)[1] if ":" in MODEL else MODEL

# Langfuse 中该应用的 trace 名称,便于筛选与统计
TRACE_NAME = "deep-research-agent"


def langfuse_configured() -> bool:
    """是否已配置 Langfuse 密钥(用于在 Langfuse / LangSmith 之间二选一)。"""
    return bool(
        os.environ.get("LANGFUSE_PUBLIC_KEY")
        and os.environ.get("LANGFUSE_SECRET_KEY")
    )


def invoke_research(query: str, langfuse_handler=None):
    """组装并运行调研 agent。传入 langfuse_handler 时启用 Langfuse 追踪。"""
    agent = create_deep_agent(
        model=MODEL,
        tools=[internet_search],
        system_prompt=research_instructions,
    )
    config = {"callbacks": [langfuse_handler]} if langfuse_handler else {}
    return agent.invoke(
        {"messages": [{"role": "user", "content": query}]},
        config=config,
    )


def main():
    parser = argparse.ArgumentParser(description="深度调研 Agent")
    parser.add_argument(
        "query",
        nargs="?",
        default=DEFAULT_QUERY,
        help=f"调研问题,默认为 '{DEFAULT_QUERY}'",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="PATH",
        default=None,
        help="报告保存路径,默认保存到 outputs/ 下的自动命名文档",
    )
    args = parser.parse_args()

    # 链路追踪二选一:
    # - 配置了 Langfuse 密钥 → 用 Langfuse 追踪,并关闭 LangSmith 避免重复上报
    # - 否则 → 走 LangSmith(需设置 LANGCHAIN_TRACING_V2=true + LANGCHAIN_API_KEY)
    if langfuse_configured():
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        langfuse = get_client()
        # 根 span 的 input/output 会作为 trace 的 input/output 展示在表格里,
        # 因此显式设置为用户问题与最终回答
        with langfuse.start_as_current_observation(
            as_type="span", name="run-research", input=args.query
        ) as run_span:
            with propagate_attributes(
                trace_name=TRACE_NAME,
                tags=["deep-research", "agent"],
                metadata={"query": args.query, "model": MODEL_NAME},
            ):
                # 在追踪上下文内初始化回调,使其继承 trace 的属性并嵌套在正确层级
                langfuse_handler = CallbackHandler()
                result = invoke_research(args.query, langfuse_handler)
            run_span.update(output=result["messages"][-1].content)
        # CLI 是短生命周期进程:必须显式 flush,确保所有观测在退出前上报
        langfuse.flush()
    else:
        result = invoke_research(args.query)

    content = result["messages"][-1].content

    # 打印结果并保存为 markdown 文档
    print(content)
    saved_path = save_report(content, args.query, args.output)
    print(f"\n[已保存] {saved_path}")


if __name__ == "__main__":
    main()
