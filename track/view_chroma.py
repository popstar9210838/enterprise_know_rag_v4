"""
查看 ChromaDB 向量数据库中的数据情况。
"""
import os
import string
import chromadb


def safe_preview(text, max_len=100):
    """清洗文本，移除不可打印字符，截断到安全长度。"""
    if not text:
        return "(空)"
    # 只保留可打印的中英文 + 常见符号
    printable = set(string.printable)
    cleaned = "".join(c if c in printable or "一" <= c <= "鿿" or c in "　、。，．；" else " " for c in text)
    cleaned = cleaned.replace("\n", " ").replace("\r", " ")
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len] + "..."
    return cleaned


# 基于脚本位置定位 chroma_db，不依赖 CWD
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
chroma_path = os.path.join(project_root, "chroma_db")

client = chromadb.PersistentClient(path=chroma_path)

# 列出所有集合
cols = client.list_collections()
print("Collections:", [c.name for c in cols])
maxCount = 50

for col in cols:
    total = col.count()
    print(f"\n{'=' * 60}")
    print(f"Collection: {col.name}  (total: {total})")
    print(f"{'=' * 60}")

    res = col.get(limit=maxCount, include=["documents", "metadatas"])

    ids = res["ids"]
    docs = res["documents"] or []
    metas = res["metadatas"] or []

    for i, (doc_id, doc, meta) in enumerate(zip(ids, docs, metas)):
        source = meta.get("source", meta.get("file_name", "unknown")) if meta else "unknown"
        print(f"\n  [{i+1}] ID: {doc_id}")
        print(f"      Source: {source}")
        print(f"      Content: {safe_preview(doc)}")