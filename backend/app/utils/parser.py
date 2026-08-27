"""文档解析：从简实现，支持 TXT / Markdown，后续扩展 PDF/Word。"""

from app.core.exceptions import BizError

SUPPORTED_TYPES = {"txt", "md", "markdown"}


def parse_content(filename: str, raw: bytes) -> str:
    """解析文档内容为纯文本。

    :param filename: 文件名（用于判断类型）
    :param raw: 文件字节内容
    :return: 解析后的文本
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in SUPPORTED_TYPES:
        raise BizError(
            400,
            40015,
            f"暂不支持的文件类型：.{ext}（当前支持 txt/md）",
        )

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw.decode("gbk")
        except UnicodeDecodeError:
            raise BizError(400, 40016, f"文件编码无法识别：{filename}")

    return text.strip()
