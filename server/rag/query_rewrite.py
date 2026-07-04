"""
查询重写器 —— 用 LLM 将用户问题改写为更利于检索的查询文本。

改写结果仅用于向量/BM25 检索，LLM 生成答案时仍使用原始问题。
"""
from llama_index.core import Settings
from llama_index.core.indices.query.query_transform.base import BaseQueryTransform
from llama_index.core.prompts import PromptTemplate
from llama_index.core.prompts.mixin import PromptDictType
from llama_index.core.schema import QueryBundle

REWRITE_PROMPT = PromptTemplate(
    "你是一个知识库搜索查询优化专家。\n"
    "把用户问题改写得更具体、包含更多关键词和同义词，以提高检索命中率。\n"
    "只返回改写后的问题，不要解释，不要添加任何额外内容。\n"
    "\n"
    "原始问题: {query_str}\n"
    "改写问题: "
)


class QueryRewriteTransform(BaseQueryTransform):
    """查询改写变换器：将原始问题改写为检索友好的查询文本。

    query_str 和 custom_embedding_strs 均使用改写结果。
    TransformRetriever 仅影响检索阶段，LLM 生成答案时 RetrieverQueryEngine
    仍使用引擎层的原始 query_bundle，因此原文不会被改写覆盖。
    """

    def __init__(self, llm=None):
        super().__init__()
        self._llm = llm or Settings.llm

    def _get_prompts(self) -> PromptDictType:
        return {"rewrite_prompt": REWRITE_PROMPT}

    def _update_prompts(self, prompts: PromptDictType) -> None:
        if "rewrite_prompt" in prompts:
            global REWRITE_PROMPT
            REWRITE_PROMPT = prompts["rewrite_prompt"]

    def _run(self, query_bundle: QueryBundle, metadata: dict) -> QueryBundle:
        # print("query_rewrite run...")
        rewritten = self._llm.predict(
            REWRITE_PROMPT,
            query_str=query_bundle.query_str,
        )
        rewritten = rewritten.strip()
        return QueryBundle(
            query_str=rewritten,                          # 改写文本供 BM25 分词用
            custom_embedding_strs=[rewritten],            # 改写文本供向量检索用
        )
