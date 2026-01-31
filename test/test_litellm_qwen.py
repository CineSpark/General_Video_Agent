from litellm import acompletion
import os
from dotenv import load_dotenv
import json
import asyncio, os, traceback

# 从 .env 文件加载环境变量
load_dotenv()

base_url = os.getenv('DASHSCOPE_BASE_URL')
print("base_url: ", base_url)

# response = completion(
#     model="dashscope/qwen-max-latest",
#     messages=[
#         {"role": "user", "content": "hello from litellm"}
#     ],
#     api_base=base_url
# )

# print("response: ", response['choices'][0]['message']['content'])

# # 保存response到json文件
# with open("test_litellm.json", "w", encoding="utf-8") as f:
#     json.dump(response.model_dump(), f, indent=2, ensure_ascii=False)

async def completion_call():
    try:
        print("test acompletion + streaming")
        response = await acompletion(
            model="dashscope/qwen-max-latest", 
            messages=[{"content": "Hello, how are you?", "role": "user"}], 
            stream=True,
            api_base=base_url
        )
        
        full_response = ""
        
        async for chunk in response:
            print("="*100)
            print(json.dumps(chunk.model_dump(), indent=2, ensure_ascii=False))
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
        
        print("full_response: ", full_response)
        
    except:
        print(f"error occurred: {traceback.format_exc()}")
        pass

asyncio.run(completion_call())