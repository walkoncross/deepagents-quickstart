"""Agent 可用的工具集。"""
import os
from typing import Literal

from dotenv import load_dotenv
from tavily import TavilyClient

# 加载 .env 中的环境变量(TAVILY_API_KEY 等)
load_dotenv()

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )
