import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.tool.upload_to_tos import UploadToTOS
import asyncio

local_path = "/Users/lxh/codebase/crengine/general_video_agent/General_Video_Agent/asset/test/cat.jpg"
introduction = "use UploadToTOS to upload the cat.jpeg file to TOS"

async def main():
    tool = UploadToTOS()
    result = await tool.execute(local_path=local_path, introduction=introduction)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())