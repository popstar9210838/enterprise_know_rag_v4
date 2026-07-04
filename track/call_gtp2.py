from transformers import AutoModelForCausalLM,AutoModel, AutoTokenizer,pipeline

model_dir = r'D:\python\enterprise_know_rag_v4\track\models\models--uer--gpt2-chinese-cluecorpussmall\snapshots\c2c0249d8a2731f269414cc3b22dff021f8e07a3'

model = AutoModelForCausalLM.from_pretrained(model_dir)

# print(model)
# exit()
tokenizer = AutoTokenizer.from_pretrained(model_dir)

generator = pipeline("text-generation",model= model, tokenizer=tokenizer)

output = generator(
    "今天晚上不想做饭了",
    max_length=50,
    num_return_sequences=1,
    truncation=True,
    temperature = 0,
    top_k = 50,
    top_p = 0.9,
    clean_up_tokenization_spaces = True
)

print(output)

