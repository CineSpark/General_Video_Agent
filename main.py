from src.logger.logging import LogConfig
from loguru import logger
from src.agent.main import MainAgent
import asyncio
from src.event.events import EventType

LogConfig.init_logger()

async def main():
    prompt = "You are a useful assistant!"
    user_message = "I want to upload the cat picture to TOS, and the path is **/Users/lxh/codebase/crengine/general_video_agent/General_Video_Agent/asset/test/cat.jpg**"
    user_id = "user_123"
    session_id = "session_123"
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
