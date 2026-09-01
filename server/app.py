"""
FastAPI 服务 —— 暴露 RAG 门面的所有能力。

Usage:
    python -m server.app
    uvicorn server.app:app --reload
"""
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.routing import Route

from server.config_loader import mcp_config, rag_config, server_config
from server.mcp_server import build_http_app as mcp_build_http_app, mcp as mcp_srv, set_rag as mcp_set_rag
from server.monitoring import setup_logging
from server.rag import RAG

# 模块加载即配置日志，确保 uvicorn worker 启动消息也归入统一格式
setup_logging(rag_config)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag
    async with AsyncExitStack() as stack:
        rag = RAG(config=rag_config)  # 重量级初始化仅一次，REST 与 MCP 共用
        mcp_set_rag(rag)
        if mcp_config.enabled:
            # FastMCP 内嵌 Starlette 必须由父 app 的 lifespan 启动其 session_manager
            await stack.enter_async_context(mcp_srv.session_manager.run())
        yield


app = FastAPI(title="企业知识库 RAG", lifespan=lifespan)
rag: Optional[RAG] = None  # 启动后由 lifespan 填充

# 静态文件 — data/ 目录下的文档可通过 /files/ 访问
app.mount("/files", StaticFiles(directory=rag_config.paths.data_dir), name="files")

# CORS — 允许前端开发服务器跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=server_config.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP — 将 RAG 查询暴露为 MCP 工具（streamable HTTP，供 Claude 等客户端调用）
if mcp_config.enabled:
    # Mount 处理 /mcp/ 子路径；裸前缀 /mcp 不匹配 Mount 正则（prefix/{path:path}），
    # 由精确 Route 承接 —— 两者都经 _RootRewrite 把边界路径改写为内层 "/" 路由，
    # 避免依赖客户端的 307 跟随。
    app.mount(mcp_config.mount_path, mcp_build_http_app())
    app.router.routes.append(
        Route(
            mcp_config.mount_path,
            endpoint=mcp_build_http_app(mcp_config.mount_path),
            methods=["GET", "POST"],
        )
    )


@app.get("/")
def root():
    return {"status": "ok", "chunks": rag.chunk_count}


@app.get("/sample-questions")
def sample_questions():
    return {"questions": rag_config.files.sample_questions}


@app.get("/preview")
def preview(file: str):
    """返回文档原始全文（从 ChromaDB 按 file_name 查），供浏览器直接展示。"""
    from fastapi.responses import PlainTextResponse
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    client = chromadb.PersistentClient(
        path=rag.persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    try:
        collection = client.get_collection(name=rag.collection_name)
        results = collection.get(
            where={"file_name": file},
            include=["documents", "metadatas"],
        )
    except Exception:
        raise HTTPException(404, f"文档不存在: {file}")

    if not results["documents"]:
        raise HTTPException(404, f"文档不存在: {file}")

    # 按页码排序后拼接
    items = list(zip(results["documents"], results["metadatas"] or []))
    items.sort(key=lambda x: (x[1].get("page", 0) if "page" in x[1] else 0))
    return PlainTextResponse("\n".join(t for t, _m in items))


# ══════════════════════════════════════════════════════════════
# 索引管理
# ══════════════════════════════════════════════════════════════

@app.get("/chunks")
def get_chunks():
    return {"chunks": rag.chunk_count}


@app.post("/build")
def build():
    count = rag.build_index()
    return {"ok": True, "chunks": count}


@app.post("/rebuild")
def rebuild():
    count = rag.rebuild_index()
    return {"ok": True, "chunks": count}


@app.post("/ingest")
def ingest():
    count = rag.ingest_index()
    return {"ok": True, "chunks": count}


@app.delete("/index")
def delete():
    rag.delete_index()
    return {"ok": True}


@app.post("/upload")
async def upload(files: list[UploadFile] = File(...)):
    """批量上传文件到 data/ 目录，配合增量入库使用。"""
    saved = []
    data_dir = Path(rag_config.paths.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        path = data_dir / f.filename
        content = await f.read()
        path.write_bytes(content)
        saved.append(f.filename)
    return {"ok": True, "saved": saved, "count": len(saved)}


# ══════════════════════════════════════════════════════════════
# 查询
# ══════════════════════════════════════════════════════════════

@app.post("/query")
def query(body: dict):
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(400, "question 不能为空")
    return rag.query(question)


@app.post("/query/stream")
def query_stream(body: dict):
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(400, "question 不能为空")

    gen = rag.query_stream(question)

    def _generate():
        import json
        try:
            first = next(gen)
        except StopIteration:
            yield "data: [DONE]\n\n"
            return
        if isinstance(first, str) and first.startswith("[ERROR]"):
            yield f"data: [ERROR] {first}\n\n"
            yield "data: [DONE]\n\n"
            return
        # first 是 sources list
        yield f"data: {json.dumps({'type': 'sources', 'sources': first}, ensure_ascii=False)}\n\n"
        for token in gen:
            yield f"data: {json.dumps({'type': 'token', 'token': token}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.app:app",
        host=server_config.host,
        port=server_config.port,
        reload=server_config.reload,
    )