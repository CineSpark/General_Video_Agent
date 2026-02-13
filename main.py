from src.logger.logging import LogConfig
from loguru import logger
from src.agent.main import MainAgent
import asyncio
from src.event.events import EventType

LogConfig.init_logger()

async def main():
#     prompt = """You are a helpful assistant that can call tools.

# Rules:
# - You may call at most ONE tool per model invocation.
# - If multiple files need to be uploaded, upload them sequentially.
# - After a tool call, wait for the tool result before deciding the next action.
# - Use the information from previous tool results to decide what to do next.
# """
#     user_message = """I want to upload two pictures to TOS.

# The pictures are:
# 1. cat picture: /Users/lxh/codebase/crengine/general_video_agent/General_Video_Agent/asset/test/cat.jpg
# 2. dog picture: /Users/lxh/codebase/crengine/general_video_agent/General_Video_Agent/asset/test/dog.jpg

# **https://lingee-video.tos-cn-beijing.volces.com/files/cat.jpg**

# Please upload them one by one.
# """

#     prompt = """
# You are a helpful assistant that can call tools.

# Rules:
# - You must call at most ONE tool per model invocation.
# - If a picture needs to be analyzed, you MUST upload it first using the UploadToTOS tool.
# - Do not call MediaAnalyze until a valid TOS URL is obtained from UploadToTOS.
# - After a tool call, wait for the tool result before deciding the next action.
# - Use the tool result from previous steps as input for the next step. 
# """
    prompt = """
You are a help assistant!

If a TODO list is created, you should follow it strictly.
"""

# Rules:
# - You must call at most ONE tool per model invocation.
# - If a picture needs to be analyzed, you MUST upload it first using the UploadToTOS tool.
# - Do not call MediaAnalyze until a valid TOS URL is obtained from UploadToTOS.
# - After a tool call, wait for the tool result before deciding the next action.
# - Use the tool result from previous steps as input for the next step. 
#     user_message = """
# I want to analyze two pictures. Use the TodoWrite tool to create a todo list to record the task planning and progress.

# The local file path is:
# - /Users/lxh/codebase/crengine/general_video_agent/General_Video_Agent/asset/test/cat.jpg
# - /Users/lxh/codebase/crengine/general_video_agent/General_Video_Agent/asset/test/dog.jpg

# Please upload the picture to TOS first.
# After you obtain the TOS URL, analyze the picture using that URL.

#     """

#     user_message = """
# 我想要分析两张图片，使用 TodoWrite 这个工具创建 Todo 列表来记录任务规划和任务进度。

# 本地文件路径是：
# - /Users/lxh/codebase/crengine/general_video_agent/General_Video_Agent/asset/test/cat.jpg
# - /Users/lxh/codebase/crengine/general_video_agent/General_Video_Agent/asset/test/dog.jpg

# 请先上传图片到 TOS，然后使用 TOS 的 URL 分析图片。上传分析完第一张图片后，再上传第二张图片，并分析第二张图片。

# 使用 task 工具创建一个任务，并委托 Analyzer 子代理来上传图片和分析图片。
# """

#     user_message = """
# 我想要分析一个视频,

# /Users/lxh/codebase/crengine/general_video_agent/General_Video_Agent/asset/test/002.mp4

# 使用 task 工具创建一个任务，并委托 Analyzer 子代理来上传视频和分析视频。
# """

    user_message = "what is your name?"

    user_id = "user_123"
    session_id = "session_456"
    invocation_id = "invocation_123"
    main_agent = MainAgent(
        prompt=prompt, 
        user_message=user_message,
        user_id=user_id,
        session_id=session_id,
        invocation_id=invocation_id,
    )

    message_generator = main_agent.handle_user_message()

    async for chunk in message_generator:
        if chunk.type == EventType.COMPLETE_RESPONSE or chunk.type == EventType.COMPLETE_CHOICE:
            print(chunk.model_dump(exclude_unset=True, exclude_none=True))
            print("\n")
            if chunk.type == EventType.COMPLETE_RESPONSE:
                logger.info(f"Complete response: {chunk.content}")

if __name__ == "__main__":
    asyncio.run(main())
