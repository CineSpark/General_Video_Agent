from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os
import uuid

from ..logger.logging import logger
from ..utils.count_tokens import count_tokens

GENERIC_VIDEO_MESSAGE_ABSTRACT_SYSTEM_PROMPT = """你是一名专业助理，专门负责总结用户和Agent的对话。你的任务是将用户与视频剪辑处理Agent之间的交互历史转换为清晰、结构化的摘要，使视频剪辑Agent能够快速理解上下文并高效继续提供支持。

请严格按照下方 JSON 格式输出摘要：

{
  "user_intent": "用户的主要需求与意图",
  "key_issues": ["问题 1", "问题 2", "问题 3"],
  "video_editing_services": ["相关视频剪辑服务 1", "相关视频剪辑服务 2"],
  "video_editing_problems": [
    {
      "problem": "问题的详细描述",
      "solution": "已提供的解决方案",
      "status": "已解决 / 部分解决 / 未解决"
    }
  ],
  "user_messages": ["用户消息 1", "用户消息 2"],
  "key_responses":["关键回复 1", "关键回复 2"],
  "pending_tasks": ["待办事项 1", "待办事项 2"],
  "current_status": "当前处理状态",
  "next_steps": "建议的下一步行动"
}

要求：
1. **摘要控制在 3500 tokens 以内；**
2. 保持客观，并保留上下文连续性，准确反映对话内容；
3. 聚焦用户的核心需求与问题；
4. 记录视频剪辑处理Agent提供的所有解决方案及其结果；
5. 识别未解决的问题与需要跟进的事项；
6. 确保摘要全面、清晰、易于理解。
"""


GENERIC_VIDEO_MESSAGE_ABSTRACT_PROMPT = """请分析以下对话，并严格按照系统提示中指定的 JSON 格式生成结构化摘要：

对话历史：
{message_history}

请仔细分析对话内容，提取关键信息，并按要求的 JSON 格式输出摘要。"""

def _summarize_messages(messages_content: list) -> str:
    """
    调用 LLM 对消息内容进行摘要    # todo
    """
    try:
        from litellm import completion

        # 设置环境变量（可以通过参数传入或从配置读取）
        api_key = os.getenv("OPENAI_API_KEY", "sk-K5uhRfyp9FvdTRPXxtZ2fGVvQ9RJBkyNoeyhbmUtV4Lls14h")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.zetatechs.com/v1")

        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_BASE_URL"] = base_url

        # 构建消息内容
        content_parts = []
        for msg in messages_content:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            content_parts.append(f"{role}: {content}")

        combined_content = "\n".join(content_parts)

        response = completion(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": GENERIC_VIDEO_MESSAGE_ABSTRACT_SYSTEM_PROMPT},
                {"role": "user", "content": GENERIC_VIDEO_MESSAGE_ABSTRACT_PROMPT.format(message_history=combined_content)}
            ],
        )

        summary = response.choices[0].message.content
        return summary if summary else ""

    except Exception as e:
        logger.error(f"LLM 摘要生成失败: {e}")
        raise e

class MySQLAbstractor:
    def __init__(self, db_url: str, **kwargs):
        """
        初始化MySQL会话服务
        """
        try:
            self.engine = create_engine(db_url, **kwargs)
            self.SessionLocal = sessionmaker(bind=self.engine)

            # 测试连接
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("MySQL连接成功")
        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
            raise e
    
    def check_threshold(self,user_id: str, session_id: str, threshold: int=40) -> bool:
        """
        检查用户会话的累计token使用量是否超过阈值
        """
        try:
            with self.SessionLocal() as db_session:
                query_sql = text(
                    """
                    SELECT MAX(accumulated_usage) AS accumulated_usage
                    FROM messages
                    WHERE user_id = :user_id AND session_id = :session_id
                """
                )
                result = db_session.execute(query_sql, {"user_id": user_id, "session_id": session_id})
                row = result.fetchone()
                accumulated_usage = row.accumulated_usage if row and row.accumulated_usage else 0
                return accumulated_usage > threshold
        except Exception as e:
            logger.error(f"检查用户会话的累计token使用量是否超过阈值失败: {e}")
            raise e
    
    def update_with_abstract(self, user_id: str, session_id: str) -> str:
        """
        对会话消息进行摘要并更新数据库

        1. 根据 user_id, session_id 从 messages 表查询所有记录
        2. 将内容发送给 LLM 生成摘要
        3. 删除原有记录，插入新的摘要记录

        返回: 生成的摘要内容
        """
        try:
            with self.SessionLocal() as db_session:
                # 1. 查询所有消息记录
                query_sql = text(
                    """
                    SELECT role, content
                    FROM messages
                    WHERE user_id = :user_id AND session_id = :session_id
                    ORDER BY created_at ASC
                """
                )
                result = db_session.execute(
                    query_sql,
                    {"user_id": user_id, "session_id": session_id}
                )
                rows = result.fetchall()

                if not rows:
                    logger.info(f"[{user_id}] [{session_id}] 没有消息记录需要摘要")
                    return ""

                # 转换为字典列表
                messages_content = [{"role": row.role, "content": row.content} for row in rows]

                # 调用 LLM 生成摘要
                summary = _summarize_messages(messages_content)
                # summary = "test abstract summary"

                # 删除原有消息记录
                delete_sql = text(
                    """
                    DELETE FROM messages
                    WHERE user_id = :user_id AND session_id = :session_id
                """
                )
                db_session.execute(
                    delete_sql,
                    {"user_id": user_id, "session_id": session_id}
                )

                # 插入新的摘要记录
                abstract_event_id = f"abstract_{uuid.uuid4().hex[:16]}"
                insert_sql = text(
                    """
                    INSERT INTO messages
                    (event_id, user_id, session_id, role, content, created_at, token_usage, accumulated_usage)
                    VALUES (:event_id, :user_id, :session_id, :role, :content, NOW(), :token_usage, :accumulated_usage)
                """
                )

                db_session.execute(
                    insert_sql,
                    {
                        "event_id": abstract_event_id,
                        "user_id": user_id,
                        "session_id": session_id,
                        "role": "assistant",  # 摘要作为 assistant 的消息
                        "content": "[abstract]" + summary,
                        "token_usage": count_tokens(summary),  # 简单使用字符数作为 token 估计
                        "accumulated_usage": count_tokens(summary),
                    }
                )
                db_session.commit()

                logger.info(
                    f"[{user_id}] [{session_id}] 消息摘要更新成功，"
                    f"原始记录数: {len(rows)}, 摘要长度: {len(summary)}"
                )
                return summary

        except Exception as e:
            logger.error(f"[{user_id}] [{session_id}] 消息摘要更新失败: {e}")
            raise e
    
    def close(self):
        """
        关闭数据库连接
        """
        if hasattr(self, "engine"):
            self.engine.dispose()
            logger.info("MySQL connection closed")
