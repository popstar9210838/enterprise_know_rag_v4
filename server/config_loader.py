"""
统一配置加载器 —— 读项目根 config.yaml，暴露 rag_config / server_config 两个单例。

Usage:
    from server.config_loader import rag_config, server_config
"""
import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
with open(_CONFIG_PATH, encoding="utf-8") as _f:
    _cfg = yaml.safe_load(_f)

# 注意：HuggingFace 离线相关环境变量 (HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE
# / HF_HOME / HF_HUB_CACHE) 由 entrypoint.sh 统一设置，此处不再重复。
# 非 Docker 环境下如需离线，请手动 export 或在 .env 中设置。


def _env_or(key: str, default):
    """环境变量覆盖 YAML 默认值，自动类型转换。"""
    val = os.getenv(key.upper())
    if val is None:
        return default
    if isinstance(default, bool):
        return val.lower() in ("1", "true", "yes")
    if isinstance(default, (int, float)):
        return type(default)(val)
    if isinstance(default, list):
        return [x.strip() for x in val.split(",")]
    if isinstance(default, set):
        return set(x.strip() for x in val.split(","))
    return val


# ── Server dataclass ──────────────────────────────────────────────────

@dataclass
class ServerConfig:
    host: str
    port: int
    reload: bool
    cors_origins: list[str]


@dataclass
class MCPConfig:
    enabled: bool
    mount_path: str


# ── RAG dataclasses ───────────────────────────────────────────────────

@dataclass
class LLMConfig:
    model: str
    api_base: str
    temperature: float
    max_tokens: int
    context_window: int
    streaming: bool


@dataclass
class EmbeddingConfig:
    model_name: str
    device: str


@dataclass
class ChunkingConfig:
    chunk_size: int
    chunk_overlap: int


@dataclass
class ChromaDBConfig:
    collection: str
    persist_dir: str
    hnsw_space: str


@dataclass
class PathsConfig:
    data_dir: str


@dataclass
class RetrievalConfig:
    vector_top_k: int
    bm25_top_k: int
    final_top_k: int
    rrf_k: int
    response_mode: str
    query_rewrite: bool
    rerank: bool
    rerank_model: str
    rerank_top_n: int


@dataclass
class FilesConfig:
    supported_extensions: list
    source_preview_len: int
    sample_questions: list


@dataclass
class QualityConfig:
    min_chinese_ratio: float


@dataclass
class MonitoringConfig:
    log_level: str
    log_format: str
    log_file: str
    log_max_bytes: int
    log_backup_count: int


@dataclass
class RagConfig:
    llm: LLMConfig
    embedding: EmbeddingConfig
    chunking: ChunkingConfig
    chromadb: ChromaDBConfig
    paths: PathsConfig
    retrieval: RetrievalConfig
    files: FilesConfig
    quality: QualityConfig
    monitoring: MonitoringConfig


# ── 加载逻辑 ──────────────────────────────────────────────────────────

def _load_rag_config() -> RagConfig:
    c = _cfg
    return RagConfig(
        llm=LLMConfig(
            model=_env_or("LLM_MODEL", c["llm"]["model"]),
            api_base=_env_or("LLM_API_BASE", c["llm"]["api_base"]),
            temperature=_env_or("LLM_TEMPERATURE", c["llm"]["temperature"]),
            max_tokens=_env_or("LLM_MAX_TOKENS", c["llm"]["max_tokens"]),
            context_window=_env_or("LLM_CONTEXT_WINDOW", c["llm"]["context_window"]),
            streaming=_env_or("LLM_STREAMING", c["llm"]["streaming"]),
        ),
        embedding=EmbeddingConfig(
            model_name=_env_or("EMBEDDING_MODEL_NAME", c["embedding"]["model_name"]),
            device=_env_or("EMBEDDING_DEVICE", c["embedding"]["device"]),
        ),
        chunking=ChunkingConfig(
            chunk_size=_env_or("CHUNKING_CHUNK_SIZE", c["chunking"]["chunk_size"]),
            chunk_overlap=_env_or("CHUNKING_CHUNK_OVERLAP", c["chunking"]["chunk_overlap"]),
        ),
        chromadb=ChromaDBConfig(
            collection=_env_or("CHROMADB_COLLECTION", c["chromadb"]["collection"]),
            persist_dir=_env_or("CHROMADB_PERSIST_DIR", c["chromadb"]["persist_dir"]),
            hnsw_space=_env_or("CHROMADB_HNSW_SPACE", c["chromadb"]["hnsw_space"]),
        ),
        paths=PathsConfig(
            data_dir=_env_or("PATHS_DATA_DIR", c["paths"]["data_dir"]),
        ),
        retrieval=RetrievalConfig(
            vector_top_k=_env_or("RETRIEVAL_VECTOR_TOP_K", c["retrieval"]["vector_top_k"]),
            bm25_top_k=_env_or("RETRIEVAL_BM25_TOP_K", c["retrieval"]["bm25_top_k"]),
            final_top_k=_env_or("RETRIEVAL_FINAL_TOP_K", c["retrieval"]["final_top_k"]),
            rrf_k=_env_or("RETRIEVAL_RRF_K", c["retrieval"]["rrf_k"]),
            response_mode=_env_or("RETRIEVAL_RESPONSE_MODE", c["retrieval"]["response_mode"]),
            query_rewrite=_env_or("RETRIEVAL_QUERY_REWRITE", c["retrieval"]["query_rewrite"]),
            rerank=_env_or("RETRIEVAL_RERANK", c["retrieval"]["rerank"]),
            rerank_model=_env_or("RETRIEVAL_RERANK_MODEL", c["retrieval"]["rerank_model"]),
            rerank_top_n=_env_or("RETRIEVAL_RERANK_TOP_N", c["retrieval"]["rerank_top_n"]),
        ),
        files=FilesConfig(
            supported_extensions=_env_or("FILES_SUPPORTED_EXTENSIONS", c["files"]["supported_extensions"]),
            source_preview_len=_env_or("FILES_SOURCE_PREVIEW_LEN", c["files"]["source_preview_len"]),
            sample_questions=_env_or("FILES_SAMPLE_QUESTIONS", c["files"]["sample_questions"]),
        ),
        quality=QualityConfig(
            min_chinese_ratio=_env_or("QUALITY_MIN_CHINESE_RATIO", c["quality"]["min_chinese_ratio"]),
        ),
        monitoring=MonitoringConfig(
            log_level=_env_or("MONITORING_LOG_LEVEL", c["monitoring"]["log_level"]),
            log_format=_env_or("MONITORING_LOG_FORMAT", c["monitoring"]["log_format"]),
            log_file=_env_or("MONITORING_LOG_FILE", c["monitoring"]["log_file"]),
            log_max_bytes=_env_or("MONITORING_LOG_MAX_BYTES", c["monitoring"]["log_max_bytes"]),
            log_backup_count=_env_or("MONITORING_LOG_BACKUP_COUNT", c["monitoring"]["log_backup_count"]),
        ),
    )


def _load_server_config() -> ServerConfig:
    c = _cfg["server"]
    return ServerConfig(
        host=_env_or("SERVER_HOST", c["host"]),
        port=_env_or("SERVER_PORT", c["port"]),
        reload=_env_or("SERVER_RELOAD", c["reload"]),
        cors_origins=_env_or("CORS_ORIGINS", c["cors_origins"]),
    )


def _load_mcp_config() -> MCPConfig:
    c = _cfg.get("mcp") or {}
    return MCPConfig(
        enabled=_env_or("MCP_ENABLED", c.get("enabled", False)),
        mount_path=_env_or("MCP_MOUNT_PATH", c.get("mount_path", "/mcp")),
    )


# 模块级单例 —— import 即加载，失败即终止
rag_config = _load_rag_config()
server_config = _load_server_config()
mcp_config = _load_mcp_config()
