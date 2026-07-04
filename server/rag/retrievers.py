"""
混合检索器 —— jieba BM25 + 语义向量 → RRF 融合。

所有参数显式传入，零配置感知。
"""
from typing import Dict, List

import jieba
import numpy as np
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, TextNode
from rank_bm25 import BM25Okapi


def _cut(text: str) -> List[str]:
    return list(jieba.cut_for_search(text))


class _JiebaBM25Retriever(BaseRetriever):
    """中文 BM25 检索器（jieba 分词）。"""

    def __init__(self, nodes: List[TextNode], top_k: int):
        super().__init__()
        self._nodes = nodes
        self._top_k = top_k
        self._corpus = [_cut(node.text) for node in nodes]
        self._bm25 = BM25Okapi(self._corpus) if self._corpus else None

    def _retrieve(self, query_bundle):
        if self._bm25 is None:
            return []
        tokens = _cut(query_bundle.query_str)
        scores = self._bm25.get_scores(tokens)
        top_indices = np.argsort(scores)[::-1][:self._top_k]
        return [
            NodeWithScore(node=self._nodes[i], score=float(scores[i]))
            for i in top_indices if scores[i] > 0
        ]


def _rrf_fusion(results_lists: List[List[NodeWithScore]], k: int) -> List[NodeWithScore]:
    """倒数排名融合（Reciprocal Rank Fusion）。"""
    node_map: Dict[str, TextNode] = {}
    scores: Dict[str, float] = {}

    for results in results_lists:
        for rank, nws in enumerate(results):
            nid = nws.node.node_id
            node_map[nid] = nws.node
            scores[nid] = scores.get(nid, 0) + 1.0 / (k + rank + 1)

    sorted_ids = sorted(scores, key=scores.get, reverse=True)
    return [NodeWithScore(node=node_map[nid], score=scores[nid]) for nid in sorted_ids]


class _HybridRetriever(BaseRetriever):
    """混合检索器：语义向量 + BM25 → RRF 融合。"""

    def __init__(
        self,
        vector_retriever: BaseRetriever,
        bm25_retriever: _JiebaBM25Retriever,
        top_k: int,
        rrf_k: int,
    ):
        super().__init__()
        self._vector_retriever = vector_retriever
        self._bm25_retriever = bm25_retriever
        self._top_k = top_k
        self._rrf_k = rrf_k

    def _retrieve(self, query_bundle):
        vec_results = self._vector_retriever.retrieve(query_bundle)
        bm25_results = self._bm25_retriever.retrieve(query_bundle)
        fused = _rrf_fusion([vec_results, bm25_results], k=self._rrf_k)
        return fused[:self._top_k]
