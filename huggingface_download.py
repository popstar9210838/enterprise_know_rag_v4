
#将模型下载
from transformers import AutoModelForCausalLM, AutoTokenizer
#将模型和分词器下载到本地，并指定保存路径

cache_dir = "models"
# model_name = "uer/gpt2-chinese-cluecorpussmall"
# model_name = "BAAI/bge-small-zh-v1.5"
model_name = "BAAI/bge-reranker-v2-m3"
# model_name = "bert-base-chinese"


#下载模型
AutoModelForCausalLM.from_pretrained (model_name, cache_dir=cache_dir)
#下载分词工具
AutoTokenizer.from_pretrained(model_name,cache_dir=cache_dir)
print(f"模型分词器已下载到:{cache_dir}")