"""
轻量级检索能力测试 —— 不调 LLM，只测 embedding + ChromaDB 检索命中率。

用法：
    python eval/retrieval_test.py              # 全量 24 题
    python eval/retrieval_test.py --top 5      # 只测前 5 题
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.config_loader import rag_config
from server.rag import RAG

QUESTIONS_FILE = Path(__file__).parent / "test_questions.json"


def get_source_names(source_nodes) -> set[str]:
    """从 LlamaIndex 响应节点中提取文件名集合。"""
    names = set()
    for node in source_nodes:
        meta = node.metadata or {}
        # metadata 中可能存 file_name、source 或 file_path
        src = meta.get("file_name") or meta.get("source") or meta.get("file_path", "")
        if src:
            # 去掉路径前缀和扩展名做匹配
            name = Path(src).stem
            names.add(name)
            names.add(str(src))  # 同时保留原始值
    return names


def match(doc_str: str, source_names: set[str]) -> bool:
    """判断 doc 字段（逗号分隔的文档名）是否命中检索来源。"""
    if not doc_str:
        return False
    expected = {d.strip().removesuffix(".md").removesuffix(".pdf").removesuffix(".txt").removesuffix(".docx")
                for d in doc_str.split(",")}
    return bool(expected & source_names)


def run_test(limit: int = None):
    print("=" * 60)
    print("[RETRIEVAL TEST] 初始化...")
    # setup_settings()
    rag = RAG(config=rag_config)
    if rag.chunk_count == 0:
        print("[ERROR] 知识库为空，请先执行 rebuild_index() / ingest_index() 入库")
        return
    engine = rag.query_engine
    if engine is None:
        print("[ERROR] 检索引擎未就绪，请检查 chroma_db 是否有效")
        return

    all_questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    questions = all_questions[:limit] if limit else all_questions

    ks = [1, 3, 5]
    results = {k: defaultdict(list) for k in ks}   # {k: {difficulty: [0/1, ...]}}
    details_by_k = {k: [] for k in ks}

    for item in questions:
        q = item["question"]
        expected_doc = item.get("doc", "")
        difficulty = item.get("difficulty", "unknown")

        response = engine.query(q)

        for k in ks:
            top_k_nodes = response.source_nodes[:k]
            top_k_names = get_source_names(top_k_nodes)
            hit = 1 if match(expected_doc, top_k_names) else 0
            results[k][difficulty].append(hit)
            results[k]["all"].append(hit)

            details_by_k[k].append({
                "question": q[:60],
                "expected": expected_doc,
                "retrieved": list(top_k_names),
                "hit": bool(hit),
                "difficulty": difficulty,
            })

    # ── 输出 ──
    for k in ks:
        print(f"\n{'─' * 60}")
        print(f"Top-{k} 检索命中率 (Hit@{k})")
        print(f"{'─' * 60}")
        for level in ["easy", "medium", "hard", "negative", "all"]:
            hits = results[k].get(level, [])
            if hits:
                rate = sum(hits) / len(hits)
                bar = "█" * int(rate * 20)
                print(f"  {level:10s}: {rate:.1%} ({sum(hits)}/{len(hits)}) {bar}")

        missed = [d for d in details_by_k[k] if not d["hit"]]
        if missed:
            print(f"\n  未命中 ({len(missed)} 题):")
            for d in missed:
                print(f"    [{d['difficulty']}] {d['question']}")
                print(f"        期望: {d['expected']}  |  检索到: {d['retrieved']}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=None)
    args = parser.parse_args()
    run_test(limit=args.top)
