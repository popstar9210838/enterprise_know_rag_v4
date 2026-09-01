"""
RAG 系统业务核心 —— 编排 loaders / quality / retrievers / vector_stores。

对外只通过 __init__.py 暴露 RAG 类。
"""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    VectorStoreIndex,
)
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike
from llama_index.core.node_parser import SentenceSplitter

from server.config_loader import RagConfig, rag_config
from .documents_loader import PDFPlumberReader, DocxReader, ExcelReader
from .documents_quality import _filter_documents
from .retrievers import _JiebaBM25Retriever, _HybridRetriever
from .vector_stores import (
    _get_vector_store,
    _chunks_count,
    _delete_collection,
    _load_all_nodes,
)


# ═══════════════════════════════════════════════════════════════════
# LlamaIndex 全局设置
# ═══════════════════════════════════════════════════════════════════

def _setup_settings(config: RagConfig):
    """配置 LlamaIndex 全局 Settings（从 RagConfig 取值）。"""
    Settings.llm = OpenAILike(
        model=config.llm.model,
        api_base=config.llm.api_base,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        is_chat_model=True,
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens,
        context_window=config.llm.context_window,
        streaming=config.llm.streaming,
    )
    Settings.embed_model = HuggingFaceEmbedding(
        model_name=config.embedding.model_name,
        device=config.embedding.device,
    )
    Settings.node_parser = SentenceSplitter(
        chunk_size=config.chunking.chunk_size,
        chunk_overlap=config.chunking.chunk_overlap,
    )
    Settings.context_window = config.llm.context_window
    Settings.num_output = config.llm.max_tokens


# ═══════════════════════════════════════════════════════════════════
# 索引构建
# ═══════════════════════════════════════════════════════════════════

def _build_index(
    data_dir: str,
    collection_name: str,
    persist_dir: str,
    supported_extensions: list,
    min_chinese_ratio: float,
    hnsw_space: str,
    docstore,
) -> VectorStoreIndex:
    """从 data_dir 加载文档 → 质检 → IngestionPipeline（分块+嵌入+验重+入库）。

    DocstoreStrategy.UPSERTS_AND_DELETE 自动处理：
      - 新增文件 → 嵌入入库
      - 内容变更 → 删旧块 + 重新嵌入
      - 未变更   → 跳过
      - 文件删除 → 清理 docstore 和向量库中的残留数据

    docstore 由调用方常驻内存，避免每次构建时全量读写 JSON。
    """
    from llama_index.core.ingestion import IngestionPipeline, DocstoreStrategy

    data_path = Path(data_dir)
    persist_path = Path(persist_dir)
    extensions_set = set(supported_extensions)

    # 1. 加载文档（全部扫描，验重交给 IngestionPipeline）
    to_load = sorted([
        p for p in data_path.iterdir()
        if p.is_file() and p.suffix.lower() in extensions_set
    ])
    if not to_load:
        logger.warning("data_dir 中无匹配文档（%s），跳过索引构建", data_dir)
        return 0
    logger.info("扫描到 %d 个文件", len(to_load))

    reader = SimpleDirectoryReader(
        input_files=to_load,
        file_extractor={
            ".pdf": PDFPlumberReader(),
            ".docx": DocxReader(),
            ".xlsx": ExcelReader(),
            ".xls": ExcelReader(),
        },
    )
    documents = reader.load_data()
    logger.info("已加载 %d 个文档片段", len(documents))

    # 2. 质检
    documents = _filter_documents(documents, min_chinese_ratio)

    # 3. 设置稳定 id_（基于文件名+页码/Sheet），使同一文件改内容后 UPSERTS 能识别并替换旧数据
    for doc in documents:
        old_id = doc.id_
        name = doc.metadata.get("file_name", old_id)
        page = doc.metadata.get("page", "")
        sheet = doc.metadata.get("sheet", "")
        if page:
            new_id = f"{name}#p{page}"
        elif sheet:
            new_id = f"{name}#s{sheet}"
        else:
            new_id = name
        doc.id_ = new_id

    # 4. IngestionPipeline：分块 + 嵌入 + 验重 + 入库 + 清理已删除
    vector_store = _get_vector_store(collection_name, persist_dir, hnsw_space)

    pipeline = IngestionPipeline(
        transformations=[Settings.node_parser, Settings.embed_model],
        vector_store=vector_store,
        docstore=docstore,
        docstore_strategy=DocstoreStrategy.UPSERTS_AND_DELETE,
    )
    pipeline.run(documents=documents, show_progress=True)
    docstore.persist(str(persist_path / "docstore.json"))

    total = _chunks_count(collection_name, persist_dir)
    logger.info("索引构建完成，共 %d 个文档块", total)

    return VectorStoreIndex.from_vector_store(
        vector_store,
        embed_model=Settings.embed_model,
    )


def _load_index(collection_name: str, persist_dir: str, hnsw_space: str) -> VectorStoreIndex:
    vector_store = _get_vector_store(collection_name, persist_dir, hnsw_space)
    return VectorStoreIndex.from_vector_store(
        vector_store,
        embed_model=Settings.embed_model,
    )


# ═══════════════════════════════════════════════════════════════════
# 查询引擎
# ═══════════════════════════════════════════════════════════════════

def _create_hybrid_query_engine(
    index: VectorStoreIndex,
    collection_name: str,
    persist_dir: str,
    vector_top_k: int,
    bm25_top_k: int,
    final_top_k: int,
    rrf_k: int,
    response_mode: str,
    streaming: bool,
    query_rewrite: bool = False,
    rerank: bool = False,
    rerank_model: str = "",
    rerank_top_n: int = 5,
) -> RetrieverQueryEngine:
    """创建单轮混合检索引擎（语义 + BM25 → RRF 融合）。"""
    from llama_index.core.response_synthesizers import get_response_synthesizer

    vector_retriever = index.as_retriever(similarity_top_k=vector_top_k)

    all_nodes = _load_all_nodes(collection_name, persist_dir)
    logger.info("[HYBRID] BM25 索引已加载 %d 个文档块", len(all_nodes))

    bm25_retriever = _JiebaBM25Retriever(all_nodes, top_k=bm25_top_k)
    hybrid = _HybridRetriever(vector_retriever, bm25_retriever, top_k=final_top_k, rrf_k=rrf_k)

    # 查询重写：改写结果仅用于检索，LLM 生成答案时仍用原始问题
    if query_rewrite:
        from server.rag.query_rewrite import QueryRewriteTransform
        from llama_index.core.retrievers import TransformRetriever
        hybrid = TransformRetriever(
            retriever=hybrid,
            query_transform=QueryRewriteTransform(),
        )

    synthesizer = get_response_synthesizer(
        streaming=streaming,
        response_mode=response_mode,
    )

    # 重排序：Cross-Encoder 对 RRF 融合结果二次打分
    node_postprocessors = []
    if rerank:
        from llama_index.core.postprocessor import SentenceTransformerRerank
        node_postprocessors.append(
            SentenceTransformerRerank(
                model=rerank_model,
                top_n=rerank_top_n,
                trust_remote_code=True,
            )
        )

    return RetrieverQueryEngine.from_args(
        retriever=hybrid,
        response_synthesizer=synthesizer,
        node_postprocessors=node_postprocessors or None,
    )


# ═══════════════════════════════════════════════════════════════════
# RAG 门面
# ═══════════════════════════════════════════════════════════════════

class RAG:
    """企业知识库 RAG 业务门面。

    Usage:
        from server.config_loader import rag_config
        from server.rag import RAG
        rag = RAG(config=rag_config)
        rag.rebuild()
        rag.query("什么是 IT 运维？")
    """

    def __init__(
        self,
        config: RagConfig = None,
        data_dir: str = None,
        collection_name: str = None,
        persist_dir: str = None,
    ):
        if config is None:
            config = rag_config  # 兼容无参调用

        self.config = config

        if data_dir is None:
            data_dir = config.paths.data_dir
        if collection_name is None:
            collection_name = config.chromadb.collection
        if persist_dir is None:
            persist_dir = config.chromadb.persist_dir

        self.data_dir = data_dir
        self.collection_name = collection_name
        self.persist_dir = persist_dir
        self._index = None
        self._query_engine = None

        # docstore 常驻内存，避免每次 build 全量读写 JSON
        from llama_index.core.storage.docstore import SimpleDocumentStore
        docstore_path = Path(persist_dir) / "docstore.json"
        if docstore_path.exists():
            self._docstore = SimpleDocumentStore.from_persist_path(str(docstore_path))
        else:
            self._docstore = SimpleDocumentStore()

        _setup_settings(self.config)
        self._try_init_query_engine()

    def _try_init_query_engine(self) -> None:
        """尝试初始化引擎：库非空则加载索引并构建混合检索器，失败不抛异常。"""
        if _chunks_count(self.collection_name, self.persist_dir) == 0:
            return
        try:
            if self._index is None:
                self._index = _load_index(
                    self.collection_name, self.persist_dir,
                    hnsw_space=self.config.chromadb.hnsw_space,
                )
            if self._index is not None:
                self._query_engine = _create_hybrid_query_engine(
                    self._index,
                    collection_name=self.collection_name,
                    persist_dir=self.persist_dir,
                    vector_top_k=self.config.retrieval.vector_top_k,
                    bm25_top_k=self.config.retrieval.bm25_top_k,
                    final_top_k=self.config.retrieval.final_top_k,
                    rrf_k=self.config.retrieval.rrf_k,
                    response_mode=self.config.retrieval.response_mode,
                    streaming=self.config.llm.streaming,
                    query_rewrite=self.config.retrieval.query_rewrite,
                    rerank=self.config.retrieval.rerank,
                    rerank_model=self.config.retrieval.rerank_model,
                    rerank_top_n=self.config.retrieval.rerank_top_n,
                )
        except Exception as e:
            logger.exception("检索引擎初始化失败: %s", e)

    # ── 索引管理 ──────────────────────────────────────────────

    def build_index(self) -> int:
        """构建/增量更新索引（UPSERTS_AND_DELETE 自动验重+清理），构建后自动重建引擎。"""
        self._index = _build_index(
            data_dir=self.data_dir,
            collection_name=self.collection_name,
            persist_dir=self.persist_dir,
            supported_extensions=self.config.files.supported_extensions,
            min_chinese_ratio=self.config.quality.min_chinese_ratio,
            hnsw_space=self.config.chromadb.hnsw_space,
            docstore=self._docstore,
        )
        self._try_init_query_engine()
        return self.chunk_count

    def rebuild_index(self) -> int:
        """清空集合并全量重建，构建后自动重建引擎。"""
        _delete_collection(self.collection_name, self.persist_dir)
        # 重置 docstore，避免 UPSERTS 基于过期映射做增量
        from llama_index.core.storage.docstore import SimpleDocumentStore
        self._docstore = SimpleDocumentStore()
        self._index = None
        self._query_engine = None
        return self.build_index()

    def ingest_index(self) -> int:
        """增量入库（同 build_index，UPSERTS 自动验重），入库后自动重建引擎。"""
        return self.build_index()

    def delete_index(self) -> None:
        """删除整个向量集合（不可逆）。"""
        _delete_collection(self.collection_name, self.persist_dir)
        from llama_index.core.storage.docstore import SimpleDocumentStore
        self._docstore = SimpleDocumentStore()
        self._index = None
        self._query_engine = None

    @property
    def chunk_count(self) -> int:
        return _chunks_count(self.collection_name, self.persist_dir)

    @property
    def query_engine(self):
        """返回底层 LlamaIndex RetrieverQueryEngine，供评估等场景获取 source_nodes。"""
        return self._query_engine

    # ── 查询 ──────────────────────────────────────────────────

    def query(self, question: str) -> dict:
        """单次混合检索查询（语义 + BM25 → RRF 融合），返回 {"answer": str, "sources": list[dict]}。"""
        if self._query_engine is None:
            return {"answer": "[ERROR] 知识库为空，请先执行入库操作", "sources": []}
        response = self._query_engine.query(question)
        answer = "".join(response.response_gen) if hasattr(response, "response_gen") else str(response)
        sources = []
        for node in getattr(response, "source_nodes", []):
            meta = node.metadata or {}
            sources.append({
                "file": meta.get("file_name", "") or meta.get("source", ""),
                "score": round(node.score or 0, 4),
                "preview": (node.text or "")[:self.config.files.source_preview_len],
            })
        return {"answer": answer, "sources": sources}

    def query_stream(self, question: str):
        """流式查询：先 yield sources（list[dict]），再逐 token yield（str）。

        Usage:
            gen = rag.query_stream("问题")
            first = next(gen)
            if isinstance(first, list):  # sources
                ...
            for token in gen:            # 剩余 token
                print(token, end="", flush=True)
        """
        if self._query_engine is None:
            yield "[ERROR] 知识库为空，请先执行入库操作"
            return
        response = self._query_engine.query(question)
        # 提取 sources
        sources = []
        for node in getattr(response, "source_nodes", []):
            meta = node.metadata or {}
            sources.append({
                "file": meta.get("file_name", "") or meta.get("source", ""),
                "score": round(node.score or 0, 4),
                "preview": (node.text or "")[:self.config.files.source_preview_len],
            })
        yield sources
        # 流式 token
        for token in response.response_gen:
            yield token
