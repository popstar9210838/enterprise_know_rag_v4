import requests

# 替换为你的真实后端服务地址
url = "http://127.0.0.1:8000/query/stream"

res = requests.post(url, json={"question": "测试"}, stream=True)

# 使用 iter_lines 逐行读取，完美解决中文多字节截断问题
for line in res.iter_lines():
    if line:
        print(line.decode('utf-8'))