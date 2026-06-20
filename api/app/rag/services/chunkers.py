"""Chunking rules — mỗi loại RAG có quy tắc riêng, không dùng chung 1 splitter.

- keyword     : 1 keyword = 1 chunk
- comment     : 1 comment = 1 chunk, KHÔNG cắt câu
- social_post : title / body / CTA -> 3–6 chunk / post
"""

from typing import Dict, List


def chunk_keyword(text: str) -> List[Dict]:
    text = (text or "").strip()
    if not text:
        return []
    return [{"text": text, "chunk_type": "keyword"}]


def chunk_comment(text: str) -> List[Dict]:
    text = (text or "").strip()
    if not text:
        return []
    return [{"text": text, "chunk_type": "comment"}]


def _split_body(body: str, max_parts: int = 4) -> List[str]:
    """Tách body thành tối đa max_parts đoạn theo paragraph, không cắt câu."""
    body = (body or "").strip()
    if not body:
        return []
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    if len(paragraphs) <= 1:
        return [body]
    if len(paragraphs) <= max_parts:
        return paragraphs
    # gộp các paragraph thành đúng max_parts nhóm liên tiếp
    step = -(-len(paragraphs) // max_parts)  # ceil division
    return [
        "\n\n".join(paragraphs[i : i + step])
        for i in range(0, len(paragraphs), step)
    ]


def chunk_social(title: str, body: str, cta: str) -> List[Dict]:
    """Trả về 3–6 chunk/post: title, body (1-4 phần), cta."""
    chunks: List[Dict] = []

    title = (title or "").strip()
    cta = (cta or "").strip()

    if title:
        chunks.append({"text": title, "chunk_type": "title"})

    for part in _split_body(body, max_parts=4):
        chunks.append({"text": part, "chunk_type": "body"})

    if cta:
        chunks.append({"text": cta, "chunk_type": "cta"})

    # đảm bảo không vượt 6 chunk: gộp dần các chunk body liên tiếp
    while len(chunks) > 6:
        body_idxs = [i for i, c in enumerate(chunks) if c["chunk_type"] == "body"]
        if len(body_idxs) < 2:
            break
        i, j = body_idxs[0], body_idxs[1]
        chunks[i]["text"] = chunks[i]["text"] + "\n\n" + chunks[j]["text"]
        del chunks[j]

    return chunks
