from litellm import completion
import os
import json

## 设置环境变量
os.environ["OPENAI_API_KEY"] = "sk-K5uhRfyp9FvdTRPXxtZ2fGVvQ9RJBkyNoeyhbmUtV4Lls14h"  # 替换为您的 API key
os.environ["OPENAI_BASE_URL"] = "https://api.zetatechs.com/v1"  # 替换为您的 base URL

response = completion(
  model="gpt-4o",
  messages=[{ "content": "Hello, how are you?","role": "user"}],
)

# 打印完整response，以缩进格式化
print(json.dumps(response.model_dump(), indent=2, ensure_ascii=False))

# 保存response到json文件
with open("test_litellm.json", "w", encoding="utf-8") as f:
    json.dump(response.model_dump(), f, indent=2, ensure_ascii=False)
