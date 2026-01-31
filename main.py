from src.logger.logging import LogConfig
from loguru import logger
from src.agent.main import MainAgent
import asyncio

LogConfig.init_logger()

async def main():
    prompt = "You are a useful assistant!"
    user_message = "I want to upload the cat picture to TOS, and the path is **/Users/lxh/codebase/crengine/general_video_agent/General_Video_Agent/asset/test/cat.jpg**"
    main_agent = MainAgent(prompt=prompt, user_message=user_message)

    message_generator = main_agent.handle_user_message()

    async for chunk in message_generator:
        print(chunk)
        # if chunk.get("type") == "complete_response":
        #     print(chunk.get("content"))

if __name__ == "__main__":
    asyncio.run(main())
