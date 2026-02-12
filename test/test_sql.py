import sys
import asyncio
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.session.mysql_service import MySQLSessionService
from src.event.events import Event, EventType
from src.tool.types import ToolCallResult, ToolExeResult


async def main():
    mysql_service = MySQLSessionService(
        db_url="mysql+pymysql://root:123456@localhost:3306/video_agent",
    )

    user_id = "user_123"
    session_id = "session_789"

    try:
        # 尝试获取会话，如果不存在则创建
        session = await mysql_service.get_session(
            user_id=user_id,
            session_id=session_id
        )

        if session is None:
            print(f"Session not found, creating new session...")
            session = await mysql_service.create_session(
                user_id=user_id,
                session_id=session_id
            )
            print(f"Session created: {session.session_id}")
        else:
            print(f"Session found: {session.session_id}")

        # ========== 测试 append_event ==========

        # 1. 创建用户消息事件
        user_event = Event(
            type=EventType.USER_MESSAGE,
            event_id=f"event_user_{int(time.time() * 1000)}",
            user_id=user_id,
            session_id=session_id,
            invocation_id="invocation_001",
            author="user",
            timestamp=time.time(),
            content="你好，我想了解视频处理的相关信息",
        )
        appended_event = await mysql_service.append_event(session, user_event)
        print(f"[OK] User event appended: {appended_event.event_id}")

        # 2. 创建模型响应事件
        model_event = Event(
            type=EventType.COMPLETE_RESPONSE,
            event_id=f"event_model_{int(time.time() * 1000)}",
            user_id=user_id,
            session_id=session_id,
            invocation_id="invocation_001",
            author="main_agent",
            timestamp=time.time(),
            content="您好！视频处理功能支持格式转换、剪辑、添加水印等操作。",
            model="gpt-4",
            finish_reason="stop",
        )
        appended_event = await mysql_service.append_event(session, model_event)
        print(f"[OK] Model event appended: {appended_event.event_id}")

        # 3. 创建工具调用事件
        tool_call_event = Event(
            type=EventType.TOOL_CALL,
            event_id=f"event_tool_{int(time.time() * 1000)}",
            user_id=user_id,
            session_id=session_id,
            invocation_id="invocation_001",
            author="main_agent",
            timestamp=time.time(),
            tool_calls=[
                {
                    "id": "call_001",
                    "function": {"name": "process_video", "arguments": {"input_path": "/videos/test.mp4", "format": "mp4"}},
                }
            ],
        )
        appended_event = await mysql_service.append_event(session, tool_call_event)
        print(f"[OK] Tool call event appended: {appended_event.event_id}")

        # 4. 创建工具响应事件
        tool_response_event = Event(
            type=EventType.TOOL_RESPONSE,
            event_id=f"event_tool_resp_{int(time.time() * 1000)}",
            user_id=user_id,
            session_id=session_id,
            invocation_id="invocation_001",
            author="main_agent",
            timestamp=time.time(),
            tool_result=ToolCallResult(
                tool_call_id="call_001",
                function_name="process_video",
                result=ToolExeResult(success=True, result="/videos/output.mp4"),
            ),
        )
        appended_event = await mysql_service.append_event(session, tool_response_event)
        print(f"[OK] Tool response event appended: {appended_event.event_id}")

        # 5. 创建错误事件
        error_event = Event(
            type=EventType.ERROR,
            event_id=f"event_error_{int(time.time() * 1000)}",
            user_id=user_id,
            session_id=session_id,
            invocation_id="invocation_001",
            author="system",
            timestamp=time.time(),
            error="视频文件格式不支持",
        )
        appended_event = await mysql_service.append_event(session, error_event)
        print(f"[OK] Error event appended: {appended_event.event_id}")

        # ========== 验证数据 ==========
        print("\n--- 验证数据 ---")

        # 重新获取会话，验证事件是否正确存储
        updated_session = await mysql_service.get_session(
            user_id=user_id,
            session_id=session_id
        )

        if updated_session:
            print(f"Session ID: {updated_session.session_id}")
            print(f"User ID: {updated_session.user_id}")
            print(f"Events count: {len(updated_session.events)}")
            print("\nEvents:")
            for i, event in enumerate(updated_session.events, 1):
                print(f"  {i}. [{event.type}] author={event.author}")
                if event.content:
                    print(f"     content: {event.content[:60]}...")
                if event.tool_calls:
                    print(f"     tool_calls: {event.tool_calls}")
                if event.tool_result:
                    print(f"     tool_result: {event.tool_result}")
                if event.error:
                    print(f"     error: {event.error}")
        else:
            print("Failed to get session!")
    finally:
        # 确保关闭数据库连接
        mysql_service.close()
        print("\n[OK] Database connection closed")


if __name__ == "__main__":
    asyncio.run(main())
