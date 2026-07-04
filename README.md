# 企业知识库 RAG

基于 **LlamaIndex + ChromaDB** 的企业知识库问答系统，支持混合检索、重排序、流式输出，Docker 一键部署。

## 技术栈

| 层 | 技术 |
|---|---|
| LLM | DeepSeek Chat（OpenAI 兼容 API） |
| 嵌入模型 | BAAI/bge-small-zh-v1.5（本地运行） |
| 向量存储 | ChromaDB（HNSW + Cosine） |
| 检索 | 向量语义 + jieba BM25 + RRF 融合 |
| 重排序 | BAAI/bge-reranker-v2-m3（可选） |
| 后端 | FastAPI + uvicorn |
| 前端 | Vue 3 + Vite |
| 评估 | ragas |
| 部署 | Docker Compose（后端 + Nginx） |

## 架构

```
用户提问
  │
  ▼
FastAPI (/query · /query/stream)
  │
  ▼
RetrieverQueryEngine
  ├─ [可选] QueryRewriteTransform（LLM 改写问题，仅用于检索）
  ├─ HybridRetriever
  │    ├─ VectorIndexRetriever（ChromaDB 语义检索）
  │    └─ JiebaBM25Retriever（jieba 分词 BM25）
  │    └─ RRF 融合 → top_k 截断
  ├─ [可选] SentenceTransformerRerank（Cross-Encoder 重排序）
  └─ ResponseSynthesizer → DeepSeek → 答案 + 来源
```

## 快速开始

### Docker 部署（推荐）

```bash
# 1. 配置 API Key
echo "DEEPSEEK_API_KEY=你的密钥" > .env

# 2. 启动
docker compose up -d --build

# 3. 访问
# http://localhost
```

首次启动会自动通过 `hf-mirror.com` 下载嵌入模型，启动后即可使用。

### 本地开发

```bash
# 后端
pip install -e .
cp .env.example .env   # 填入 DEEPSEEK_API_KEY
python -m server.app    # http://localhost:8080

# 前端
cd ui && npm install && npm run dev   # http://localhost:5173
```

### CLI 模式

```bash
python -m server.cli
```

## 使用说明

1. **上传文档** — 前端管理面板上传 PDF/DOCX/Excel/Markdown/TXT
2. **同步索引** — 点击"同步索引"按钮，系统自动分块、向量化、入库
3. **开始提问** — 输入问题，获取带来源引用的回答

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 健康检查 |
| POST | `/query` | 非流式查询 |
| POST | `/query/stream` | 流式查询（SSE） |
| POST | `/build` | 增量构建索引 |
| POST | `/rebuild` | 全量重建索引 |
| POST | `/upload` | 上传文件 |
| DELETE | `/index` | 删除索引 |
| GET | `/preview?file=xxx` | 文档原文预览 |

## 配置

编辑 `config.yaml`：

```yaml
retrieval:
  vector_top_k: 10     # 语义检索条数
  bm25_top_k: 10       # BM25 检索条数
  final_top_k: 5        # 融合后保留条数
  rerank: false         # 是否开启重排序
  query_rewrite: false  # 是否开启查询重写

chunking:
  chunk_size: 512
  chunk_overlap: 50
```

支持环境变量覆盖所有配置项。

## 评估

```bash
python eval/evaluate.py --top 5     # ragas 四项指标评估
python eval/retrieval_test.py        # 检索命中率测试
```

## 项目结构

```
├── server/
│   ├── app.py                  # FastAPI 入口
│   ├── cli.py                  # CLI 交互式查询
│   ├── config_loader.py        # YAML 配置加载
│   ├── rag/
│   │   ├── rag_core.py         # RAG 门面
│   │   ├── retrievers.py       # 混合检索器
│   │   ├── documents_loader.py # 文档解析
│   │   └── query_rewrite.py    # 查询重写
│   └── monitoring/             # 日志
├── ui/                         # Vue 3 前端
├── docker/                     # Docker 配置
├── eval/                       # 评估脚本
└── data/                       # 知识库文档
```