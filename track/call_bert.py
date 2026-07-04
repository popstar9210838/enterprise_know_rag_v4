from transformers import BertForSequenceClassification, AutoTokenizer,pipeline

model_dir = r'D:\python\enterprise_know_rag_v4\track\models\models--bert-base-chinese\snapshots\8f23c25b06e129b6c986331a13d8d025a92cf0ea'

model = BertForSequenceClassification.from_pretrained(model_dir)

print(model)
# exit()
tokenizer = AutoTokenizer.from_pretrained(model_dir)

classifier = pipeline("text-classification",model= model, tokenizer=tokenizer)

output = classifier(
    "今天晚上不想做饭了"
)

print(output)

