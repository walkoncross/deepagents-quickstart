"""CLI 入口:组装 research agent 并运行。"""
import argparse

from deepagents import create_deep_agent

from quickstart.prompts import research_instructions
from quickstart.report import save_report
from quickstart.tools import internet_search

DEFAULT_QUERY = "What is langgraph?"
MODEL = "deepseek:deepseek-v4-flash"  # 可换 openai:gpt-5.5


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

    agent = create_deep_agent(
        model=MODEL,
        tools=[internet_search],
        system_prompt=research_instructions,
    )

    result = agent.invoke({"messages": [{"role": "user", "content": args.query}]})

    content = result["messages"][-1].content

    # 打印结果并保存为 markdown 文档
    print(content)
    saved_path = save_report(content, args.query, args.output)
    print(f"\n[已保存] {saved_path}")


if __name__ == "__main__":
    main()
