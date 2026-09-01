"""MCP 服务器 —— 将 RAG 查询能力暴露为 MCP 工具（streamable HTTP）。

RAG 实例由 server.app 的 lifespan 创建后通过 set_rag() 注入，
避免每个 MCP 连接重复加载嵌入模型与 BM25 索引（与 server/app.py
的模块级 rag 模式一致，避免 import 环）。
"""
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from starlette.types import ASGIApp, Receive, Scope, Send

# 模块级 RAG 持有者 —— 服务启动时由 app.lifespan 注入一次
_rag: Optional[object] = None


def set_rag(rag) -> None:
    """注入共享的 RAG 实例（启动时调用一次）。"""
    global _rag
    _rag = rag


def _get_rag():
    if _rag is None:
        raise ToolError("[ERROR] RAG 引擎尚未初始化，服务可能仍在启动中")
    return _rag


# stateless：多用户/水平扩展友好；json_response：普通 JSON 响应而非 SSE
mcp = FastMCP("enterprise-rag", stateless_http=True, json_response=True)
# 挂载前缀由 app.mount() 决定，内部路径设为根路径，避免 /mcp/mcp
mcp.settings.streamable_http_path = "/"


class _RootRewrite:
    """把挂载/路由边界上的路径统一改写为 "/"，使 POST /mcp 直达内层路由。

    Starlette Mount 的正则是 "<prefix>/{path:path}"，裸前缀 POST /mcp
    不匹配任何路由，外层 Router 回 307 → /mcp/；httpx 等不跟随重定向
    的 MCP 客户端会失败。因此除 Mount（处理 /mcp/ 子路径）外，另用一条
    精确 Route 承接裸前缀请求，两者都把边界路径改写为内层的 "/" 路由。
    """

    def __init__(self, app: ASGIApp, prefix: str = ""):
        self.app = app
        self.prefix = prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path", "") in ("", self.prefix):
            scope = dict(scope)
            scope["path"] = "/"
        await self.app(scope, receive, send)


def build_http_app(prefix: str = "") -> ASGIApp:
    """返回可挂载到 FastAPI 的 ASGI app。"""
    return _RootRewrite(mcp.streamable_http_app(), prefix)


@mcp.tool()
def rag_query(question: str) -> dict:
    """根据用户问题检索企业知识库并生成回答。

    参数:
        question: 用户的完整问题原文，请直接传原始问句，不要改写或拆分。

    返回: JSON 对象（序列化为文本）:
        {
          "answer": str,     # 基于知识库文档生成的中文回答
          "sources": [       # 引用来源；回答中引用规定时请标注对应 file
            {"file": str, "score": float, "preview": str}
          ]
        }

    使用要求:
        - 回答内容严格来自企业知识库（考勤、报销、质量、客户服务、供应链、数据安全等制度文档）。
        - 引用出处时使用 sources 中的 file 文件名与 preview 片段，不要编造来源。
        - 若知识库为空或检索不到相关内容，工具会返回错误，请如实转告用户，不要凭空作答。
        - 当用户询问公司内部制度、规定、流程、产品资料等内容时调用此工具；通用常识问题直接回答，不要调用。
    """
    question = (question or "").strip()
    if not question:
        raise ToolError("[ERROR] question 参数不能为空")
    result = _get_rag().query(question)
    if result["answer"].startswith("[ERROR]"):
        # 知识库为空等业务错误 → 以 isError 返回，避免调用方把错误串当答案引用
        raise ToolError(result["answer"])
    return result
