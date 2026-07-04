"""
命令行入口 —— 调用 RAG 门面，交互式查询知识库。

Usage:
    python -m server.cli                # 查询模式
"""
import logging
from prompt_toolkit import PromptSession

logger = logging.getLogger(__name__)
from prompt_toolkit.completion import WordCompleter

from server.config_loader import rag_config
from server.monitoring import setup_logging
from server.rag import RAG

# 斜杠命令列表，meta_dict 提供中文说明
_COMMANDS = {
    "/build": "全量构建索引",
    "/rebuild": "清空并全量重建",
    "/ingest": "增量入库",
    "/delete": "删除索引",
    "/quit": "退出",
}

_completer = WordCompleter(
    list(_COMMANDS),
    ignore_case=True,
    meta_dict=_COMMANDS,
    sentence=True,  # 仅第一个"词"做补全，后续自由输入
)


def main():
    setup_logging(rag_config)
    rag = RAG(config=rag_config)

    if rag.chunk_count == 0:
        print("[WARN] 知识库为空，请执行 /build 或 /rebuild 构建索引")

    session = PromptSession(completer=_completer)

    print("=" * 50)
    print(f"[QUERY] 知识库查询模式  |  {rag.chunk_count} 个文档块")
    print("  输入 / 弹出命令列表（Tab 补全，↑↓ 选择）")
    print("  直接输入问题开始检索")
    print("=" * 50)

    while True:
        try:
            text = session.prompt("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not text:
            continue

        # ── 退出 ──
        if text.lower() in ("quit", "exit", "/quit"):
            print("Bye!")
            break

        # ── 斜杠命令 ──
        if text.startswith("/"):
            if text == "/delete":
                rag.delete_index()
                print("[OK] 索引已删除")
            elif text == "/build":
                count = rag.build_index()
                print(f"[OK] 索引构建完成，共 {count} 个文档块")
            elif text == "/rebuild":
                count = rag.rebuild_index()
                print(f"[OK] 索引重建完成，共 {count} 个文档块")
            elif text == "/ingest":
                count = rag.ingest_index()
                print(f"[OK] 增量入库完成，共 {count} 个文档块")
            else:
                print(f"[WARN] 未知命令: {text}")
            continue

        # ── 检索查询 ──
        try:
            print("\nAI: ", end="", flush=True)
            gen = rag.query_stream(text)
            first = next(gen)
            if isinstance(first, list):
                pass  # sources，CLI 不展示
            else:
                print(first, end="", flush=True)
            for token in gen:
                print(token, end="", flush=True)
            print()
        except Exception:
            logger.exception("查询失败: %s", text[:50])
            print("\n[ERROR] 查询出错，详情见日志")


if __name__ == "__main__":
    main()
