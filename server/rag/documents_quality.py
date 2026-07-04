"""
文本质检 —— 过滤乱码、二进制、低可读性文档块。
"""
import logging
import re
from typing import List

from llama_index.core import Document

logger = logging.getLogger(__name__)


def _is_garbage(text: str, min_chinese_ratio: float) -> bool:
    """判断文本是否为垃圾（乱码 / 二进制 / 低可读性）。"""
    if not text or not text.strip():
        return True
    if text.startswith("%PDF"):
        return True

    cid_pattern = re.compile(r"<\w{4}>")
    cid_count = len(cid_pattern.findall(text))
    total_chars = len(text)
    if total_chars > 0 and cid_count / total_chars > 0.05:
        return True

    chinese_chars = len(re.findall(r"[一-鿿]", text))
    ascii_chars = len(re.findall(r"[a-zA-Z0-9]", text))
    if total_chars > 50 and (chinese_chars + ascii_chars) / total_chars < min_chinese_ratio:
        return True

    return False


def _filter_documents(documents: List[Document], min_chinese_ratio: float) -> List[Document]:
    """过滤低质量文档块。"""
    good = []
    bad_count = 0
    for doc in documents:
        if _is_garbage(doc.text, min_chinese_ratio):
            bad_count += 1
        else:
            good.append(doc)
    if bad_count > 0:
        logger.info("已过滤 %d 个低质量文档块", bad_count)
    return good
