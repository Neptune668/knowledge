"""文本切片：按段落切分，段落过长时按长度二次切分。"""

import re


def split_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[str]:
    """将文本切分为切片列表。

    :param text: 待切片文本
    :param chunk_size: 单切片目标最大字符数
    :param chunk_overlap: 相邻切片重叠字符数
    :return: 切片列表
    """
    text = text.strip()
    if not text:
        return []

    # 1. 按段落（空行）切分
    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        # 单段落超长，先按长度切分
        if len(para) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_by_len(para, chunk_size, chunk_overlap))
            continue

        # 当前块加上段落后超长，则先保存当前块
        if len(current) + len(para) + 1 > chunk_size:
            if current:
                chunks.append(current)
            current = para
        else:
            current = f"{current}\n{para}" if current else para

    if current:
        chunks.append(current)

    return chunks


def _split_by_len(text: str, chunk_size: int, overlap: int) -> list[str]:
    """按固定长度切分长文本，带重叠。"""
    result = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        result.append(text[start:end])
        if end >= n:
            break
        start = end - overlap
    return result


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数（中文按字数，英文按 4 字符 ≈ 1 token）。"""
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    other_chars = len(text) - chinese_chars
    return chinese_chars + other_chars // 4
