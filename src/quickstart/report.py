"""调研报告输出:文件名清洗与 markdown 保存。"""
import re
from datetime import datetime
from pathlib import Path

# 项目根目录 / 输出目录(以本文件位置为锚点,不依赖当前工作目录)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


def _slugify(text: str) -> str:
    """把查询文本转成安全的文件名片段(保留中文/字母/数字)"""
    slug = re.sub(r"[^\w一-鿿]+", "_", text.strip(), flags=re.UNICODE)
    return slug.strip("_")[:50] or "report"


def save_report(content: str, query: str, output: str | None = None) -> Path:
    """把调研结果保存为 markdown 文档,返回文件路径。

    output 为 None 时,自动生成 outputs/时间戳_查询片段.md;
    否则保存到指定路径(父目录自动创建)。
    """
    if output is None:
        path = OUTPUTS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}_{_slugify(query)}.md"
    else:
        path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
