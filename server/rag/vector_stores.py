"""
向量库操作 —— ChromaDB 持久化，包括增删查 + 节点加载。

所有参数显式传入，零配置感知。
"""
import logging
from typing import List

import chromadb

logger = logging.getLogger(__name__)
from chromadb.config import Settings as ChromaSettings
from llama_index.core.schema import TextNode
from llama_index.vector_stores.chroma import ChromaVectorStore


def _get_vector_store(collection_name: str, persist_dir: str, hnsw_space: str) -> ChromaVectorStore:
    """获取 ChromaDB 向量库实例。"""
    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": hnsw_space},
    )
    return ChromaVectorStore(chroma_collection=collection)


def _chunks_count(collection_name: str, persist_dir: str) -> int:
    """获取集合中的文档块数量。"""
    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    try:
        return client.get_collection(name=collection_name).count()
    except Exception:
        logger.debug("获取 chunk 数量失败（库可能尚未创建）: %s", collection_name)
        return 0


def _delete_file_chunks(file_name: str, collection_name: str, persist_dir: str) -> int:
    """删除指定文件的所有文档块，返回删除数量。"""
    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    try:
        collection = client.get_collection(name=collection_name)
        before = collection.count()
        collection.delete(where={"file_name": file_name})
        return before - collection.count()
    except Exception:
        logger.exception("删除文件块失败: %s / %s", file_name, collection_name)
        return 0


def _delete_collection(collection_name: str, persist_dir: str) -> None:
    """删除整个集合。"""
    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    try:
        client.delete_collection(name=collection_name)
        logger.info("已清空集合: %s", collection_name)
    except Exception:
        logger.exception("删除集合失败: %s", collection_name)


def _load_all_nodes(collection_name: str, persist_dir: str) -> List[TextNode]:
    """加载集合中所有节点，供 BM25 检索器构建语料。"""
    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    try:
        collection = client.get_collection(name=collection_name)
        result = collection.get(include=["documents", "metadatas"])
        nodes = []
        for doc_id, text, meta in zip(
            result["ids"], result["documents"] or [], result["metadatas"] or []
        ):
            if text:
                nodes.append(TextNode(id_=doc_id, text=text, metadata=meta or {}))
        return nodes
    except Exception as e:
        logger.exception("加载全量节点失败: %s", e)
        return []
