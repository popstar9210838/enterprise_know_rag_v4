from transformers import AutoModelForCausalLM,AutoModel, AutoTokenizer,pipeline

model_dir = r"D:\python\enterprise_know_rag_v4\track\models\models--BAAI--bge-small-zh-v1.5\snapshots\7999e1d3359715c523056ef9478215996d62a620"

model = AutoModel.from_pretrained(model_dir)
print(model)



