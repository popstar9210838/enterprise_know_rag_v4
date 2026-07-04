"""
RAG 系统评估模块 —— 使用 ragas 评测检索与生成质量。

用法：
    python eval/evaluate.py              # 完整评估（24 题）
    python eval/evaluate.py --top 5      # 只测前 5 题
"""
import json
import os
import sys
import types
from datetime import datetime
from pathlib import Path

# ── 必须在所有 HuggingFace 相关 import 之前设置，阻止联网 ──
os.environ["HF_HUB_OFFLINE"] = "1"

# ── 兼容层：ragas 0.4.3 期望 langchain_community 有 vertexai，但新版移到了 langchain_google_vertexai ──
from langchain_google_vertexai import ChatVertexAI  # noqa: E402

_m = types.ModuleType("langchain_community.chat_models.vertexai")
_m.ChatVertexAI = ChatVertexAI
sys.modules["langchain_community.chat_models.vertexai"] = _m

from openai import OpenAI as OpenAIClient  # noqa: E402
from ragas import EvaluationDataset, evaluate  # noqa: E402
from langchain_huggingface import HuggingFaceEmbeddings  # noqa: E402
from ragas.llms import llm_factory  # noqa: E402
from ragas.metrics import (  # noqa: E402
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

# 项目根目录加入路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.config_loader import rag_config  # noqa: E402
from server.rag import RAG  # noqa: E402

# ── 配置 ──
RESULTS_DIR = Path(__file__).parent / "results"
QUESTIONS_FILE = Path(__file__).parent / "test_questions.json"


def load_questions(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_evaluator_llm():
    """构建 ragas 评估器 LLM（用 DeepSeek 评判答案质量）。"""
    client = OpenAIClient(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1",
    )
    return llm_factory("deepseek-chat", client=client)


def build_evaluator_embeddings():
    """构建评估器嵌入模型（LangChain 包装，确保 embed_query 可用）。"""
    return HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5",
        model_kwargs={"device": "cpu", "local_files_only": True},
        encode_kwargs={"normalize_embeddings": True},
    )


def run_evaluation(limit: int = None):
    """主评估流程。"""
    # 1. 初始化 RAG 管道
    print("=" * 60)
    print("[EVAL] 初始化...")
    # setup_settings()
    rag = RAG(config=rag_config)
    if rag.chunk_count == 0:
        print("[ERROR] 知识库为空，请先执行 rebuild_index() / ingest_index() 入库")
        return
    engine = rag.query_engine
    if engine is None:
        print("[ERROR] 检索引擎未就绪，请检查 chroma_db 是否有效")
        return

    # 2. 加载测试题
    all_questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    questions = all_questions[:limit] if limit else all_questions
    print(f"已加载 {len(questions)} 道测试题（共 {len(all_questions)} 道）")

    # 3. 逐题查询，收集数据
    print("\n[EVAL] 逐题查询...")
    eval_data = {
        "user_input": [],
        "response": [],
        "reference": [],
        "retrieved_contexts": [],
    }
    details = []

    for i, item in enumerate(questions, 1):
        q = item["question"]
        ref = item["answer"]
        doc = item.get("doc", "")

        response = engine.query(q)
        answer = str(response)
        contexts = [node.text for node in getattr(response, "source_nodes", [])]

        eval_data["user_input"].append(q)
        eval_data["response"].append(answer)
        eval_data["reference"].append(ref)
        eval_data["retrieved_contexts"].append(contexts)

        details.append({
            "question": q,
            "reference": ref,
            "response": answer,
            "doc": doc,
            "difficulty": item.get("difficulty", ""),
            "context_count": len(contexts),
        })
        print(f"  [{i}/{len(questions)}] {q[:50]}...")

    # 4. 构建 ragas 数据集
    print("\n[EVAL] 运行 ragas 评估...")
    samples = [
        {
            "user_input": eval_data["user_input"][i],
            "response": eval_data["response"][i],
            "reference": eval_data["reference"][i],
            "retrieved_contexts": eval_data["retrieved_contexts"][i],
        }
        for i in range(len(eval_data["user_input"]))
    ]
    dataset = EvaluationDataset.from_list(samples)
    evaluator_llm = build_evaluator_llm()
    evaluator_embeddings = build_evaluator_embeddings()

    result = evaluate(
        dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ],
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
        show_progress=True,
    )

    # 5. 汇总结果
    metrics_summary = {}
    for metric_name in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        scores = result.to_pandas()[metric_name].dropna()
        metrics_summary[metric_name] = {
            "mean": round(float(scores.mean()), 4),
            "median": round(float(scores.median()), 4),
            "std": round(float(scores.std()), 4),
            "min": round(float(scores.min()), 4),
        }

    # 逐题详情
    df = result.to_pandas()
    for i, detail in enumerate(details):
        for col in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
            if col in df.columns and i < len(df):
                detail[col] = round(float(df[col].iloc[i]), 4) if not df[col].isna().iloc[i] else None

    # 6. 输出
    print("\n" + "=" * 60)
    print("[EVAL] 评估结果")
    print("=" * 60)
    for name, stats in metrics_summary.items():
        print(f"  {name:25s}  mean={stats['mean']:.4f}  median={stats['median']:.4f}  std={stats['std']:.4f}")

    # 7. 保存报告
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = {
        "timestamp": timestamp,
        "total_questions": len(questions),
        "metrics_summary": metrics_summary,
        "details": details,
    }
    report_path = RESULTS_DIR / f"report_{timestamp}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n[EVAL] 报告已保存至: {report_path}")

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG 系统评估")
    parser.add_argument("--top", type=int, default=None, help="只评估前 N 道题")
    args = parser.parse_args()

    run_evaluation(limit=args.top)
