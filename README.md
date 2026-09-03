# 企业知识库 RAG

基于 **LlamaIndex + ChromaDB** 的企业知识库问答系统：混合检索（向量 + BM25 + RRF 融合）、多格式文档解析、Vue 3 前端 + FastAPI 后端，Docker 一键部署。

## 技术栈

- **Python / FastAPI** — 后端 API 服务
- **LlamaIndex / ChromaDB** — 检索框架与向量存储
- **BGE 嵌入模型**（bge-small-zh-v1.5，本地运行）+ **DeepSeek API** — 答案生成
- **Vue 3 / Vite** — 前端页面
- **Nginx** — 静态资源 + API 反向代理
- **Docker Compose** — 部署

## 部署架构

```
浏览器 :80
  │
  ▼
Nginx ── Vue 3 静态页面（ui/dist）
  │  /query /upload /preview ... 反向代理
  ▼
FastAPI :8080
  ├─ 混合检索：向量检索 + BM25 → RRF 融合
  ├─ ChromaDB（本地持久化，docker 卷）
  └─ DeepSeek API → 生成答案
```

## 运行步骤

### Docker 部署（推荐）

```bash
# 1. 配置 API Key
echo "DEEPSEEK_API_KEY=sk-xxx" > .env

# 2. 下载嵌入模型到models文件夹（路径见 `config.yaml`，可用 `huggingface_download.py` 下载）

# 3. 启动
docker compose up -d --build

# 4. 访问 http://localhost
```

### 本地开发

```bash
# 后端
pip install -e .
python -m server.app          # http://localhost:8080

# 前端（另开终端）
cd ui && npm install
npm run dev                   # http://localhost:5173
```

## 使用

1. 将文档放入 `data/`或者在前端上传文档（支持 PDF / DOCX / Excel / Markdown / TXT）
2. 前端点击"同步索引"
3. 输入问题，获得带来源引用的回答
