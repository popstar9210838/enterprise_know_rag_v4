# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

基于 LlamaIndex + ChromaDB 的企业知识库 RAG 系统。BAAI/bge-small-zh-v1.5 本地嵌入，DeepSeek API 做 LLM 生成，Vue 3 + FastAPI 前后端。

## 常用命令

```bash
# 安装
pip install -e .
cd ui && npm install

# ── 后端 ──
python -m server.cli               # CLI 交互式查询
python -m server.app               # REST API 服务 (0.0.0.0:8080)

# ── 前端 ──
cd ui && npm run dev               # Vite (5173)，a 标签直连 8080

# 评估
python eval/evaluate.py --top 5    # ragas 评估
python eval/retrieval_test.py      # 检索命中率测试
python track/view_chroma.py        # ChromaDB 内容查看
```

## 架构

```
server/
  app.py                          # FastAPI 入口，lifespan 创建 RAG + setup_logging
  cli.py                          # prompt_toolkit CLI
  config_loader.py                # 从 config.yaml 加载 RagConfig / ServerConfig 单例
  monitoring/
    logging_config.py             # 根 logger 配置，第三方库级别控制
  rag/
    rag_core.py                   # RAG 门面 + _build_index (IngestionPipeline) + _setup_settings
    retrievers.py                 # _JiebaBM25Retriever + _HybridRetriever + RRF 融合
    query_rewrite.py              # QueryRewriteTransform（LLM 改写问题，仅用于检索）
    vector_stores.py              # ChromaDB CRUD
    documents_loader.py           # PDFPlumberReader / DocxReader / ExcelReader
    documents_quality.py          # _filter_documents() 中文低质量过滤
```

### 查询流程

```
RAG.query() / query_stream()
  └─ RetrieverQueryEngine
       ├─ [可选] TransformRetriever → QueryRewriteTransform（查询重写）
       ├─ _HybridRetriever
       │    ├─ VectorIndexRetriever（ChromaDB 语义检索）
       │    └─ _JiebaBM25Retriever（jieba 分词 BM25）
       │    └─ RRF 融合 → top_k 截断
       ├─ [可选] SentenceTransformerRerank（Cross-Encoder 重排序）
       └─ ResponseSynthesizer → DeepSeek LLM → 答案
```

### 索引构建（IngestionPipeline）

旧的手动哈希验重（`_file_hash` `_scan_files` `_diff_files` `file_hashes.json`）已删除。现在是：

```
SimpleDirectoryReader 加载 → _filter_documents 质检
  → doc.id_ = file_name（+ #p页码 后缀）
  → IngestionPipeline (UPSERTS_AND_DELETE) 自动验重 + 分块 + 嵌入 + 入库
  → docstore.persist → chroma_db/docstore.json
```

build_index / ingest_index 行为一致，前端合并为"同步索引"一个按钮。

### 配置关键字段

| 配置 | 说明 |
|---|---|
| `retrieval.query_rewrite` | 查询重写开关（默认 false） |
| `retrieval.rerank` / `rerank_model` / `rerank_top_n` | 重排序，rerank=true 启用 |
| `files.sample_questions` | 前端示例问题列表 |
| `monitoring.log_level` / `log_format` / `log_file` | 日志控制 |

## ChromaDB 存储

- `chroma_db/` — SQLite + 向量索引，集合 `rag_docs`，cosine 空间
- `chroma_db/docstore.json` — SimpleDocumentStore，存文档全文 + 节点映射 + 哈希

## 预览

`GET /preview?file=xxx` 从 ChromaDB 按 file_name 查所有 chunk，拼接返回纯文本。前端 SourceCard 链接指向此端点。

## 注意事项

- `doc.id_` 必须用 `file_name#p页码` 格式覆盖，否则多页 PDF 会互相覆盖
- `logger.exception()` 只在非预期错误使用，预期状态（如集合不存在）用 `logger.debug()`
- 日志 handler 防重复检查：`not any(isinstance(h, logging.StreamHandler) for h in root.handlers)`