import time
import uuid
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator, List

import opik

from ..prompt import (
    TASK_TOOL_DESC_PROMPT,
    get_prompt_by_name,
    PROMPT_NAME_TASK_TOOL_DESCRIPTION,
)
from ..logger import logger
from .base import BaseTool
from ..event.events import EventType, EventErrorCode
from ..shared.utils import extract_message_content


class TaskExecution:
    """任务执行跟踪器"""

    def __init__(self, task_id: str, description: str, subagent_type: str):
        self.task_id = task_id
        self.description = description
        self.subagent_type = subagent_type
        self.status = (
            "initializing"  # initializing, running, completed, error, cancelled
        )
        self.start_time = time.time()
        self.end_time = None
        self.result = None
        self.error = None
        self.progress_events = []
        self.sub_agent = None

    def update_status(self, status: str, result: Any = None, error: str = None):
        """更新任务状态"""
        self.status = status
        if result is not None:
            self.result = result
        if error:
            self.error = error
        if status in ["completed", "error", "cancelled"]:
            self.end_time = time.time()

    def get_duration(self) -> float:
        """获取执行时长"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    def add_progress_event(self, event_type: str, content: str):
        """添加进度事件"""
        self.progress_events.append(
            {"type": event_type, "content": content, "timestamp": time.time()}
        )


# https://github.com/shareAI-lab/Kode/blob/main/src/tools/TaskTool/TaskTool.tsx
class Task(BaseTool):
    def __init__(self):
        super().__init__()
        self.name = "Task"
        self.description = get_prompt_by_name(
            PROMPT_NAME_TASK_TOOL_DESCRIPTION, TASK_TOOL_DESC_PROMPT
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "A short (3-5 word) description of the task",
                },
                "prompt": {
                    "type": "string",
                    "description": "The task for the agent to perform",
                },
                "subagent_type": {
                    "type": "string",
                    "description": "The type of specialized agent to use for this task",
                },
            },
            "required": ["description", "prompt", "subagent_type"],
        }
        # 可用代理类型
        self.available_agents = {
            "material_analyzer" : "analyze the audio or video material",
            # "knowledge_base": "Search announcements and API documentation using RAG",
            # "news_search": "Search and analyze tweets and social media content",
            # "market_search": "Real-time cryptocurrency price data retrieval and market analysis",
        }

        # 任务执行状态跟踪
        self.active_tasks = {}

    def _create_sub_agent(
        self,
        subagent_type: str,
        prompt: str,
        task_id: str,
        parent_span_id: str = None,
        **context,
    ):
        """创建专业化子代理"""
        # 通用参数
        agent_kwargs = {
            "prompt": prompt,
            "sub_invocation_id": task_id,
            "parent_span_id": parent_span_id,
            **context,
        }  # 传递会话上下文

        # 根据代理类型创建对应的子代理
        if subagent_type == "knowledge_base":
            from ..agent.knowledge_agent import KnowledgeBaseAgent

            return KnowledgeBaseAgent(**agent_kwargs)
        elif subagent_type == "news_search":
            from ..agent.news_agent import NewsAgent

            return NewsAgent(**agent_kwargs)
        elif subagent_type == "market_search":
            from ..agent.market_agent import MarketAgent

            return MarketAgent(**agent_kwargs)
        else:
            raise NotImplementedError(f"Unknown subagent_type: {subagent_type}")

    async def _cleanup_task_later(self, task_id: str, delay: float = 300):
        """延迟清理任务记录（5分钟后）"""
        await asyncio.sleep(delay)
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]

    async def execute(
        self,
        description: str,
        prompt: str,
        subagent_type: str,
        # 新增会话上下文参数
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        invocation_id: Optional[str] = None,
        trace: Optional[opik.Trace] = None,
        # 新增session相关参数
        session: Optional[Any] = None,
        session_service: Optional[Any] = None,
        introduction: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        pass

    async def execute_streaming(
        self,
        description: str,
        prompt: str,
        subagent_type: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        invocation_id: Optional[str] = None,
        trace: Optional[opik.Trace] = None,
        session: Optional[Any] = None,
        session_service: Optional[Any] = None,
        introduction: Optional[str] = None,
        parent_span_id=None,
        task_id=None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute task with streaming events
        """
        validation = self.validate_params(
            description=description,
            prompt=prompt,
            subagent_type=subagent_type,
            introduction=introduction,
        )
        if not validation["success"]:
            logger.error(
                f"[{session_id}] [{invocation_id}] Tool {self.name} Parameter validation failed"
            )
            yield {
                "type": EventType.TASK_ERROR,
                "content": "Parameter validation failed",
                "error_code": EventErrorCode.TASK_PARAMETER_ERROR,
                "result": validation,
                "final": True,
                "sub_invocation_id": task_id,  # 参数验证错误时使用传入的task_id
            }
            return

        if subagent_type not in self.available_agents:
            logger.error(
                f"[{session_id}] [{invocation_id}] Tool {self.name} Unknown agent type {subagent_type}"
            )
            yield {
                "type": EventType.TASK_ERROR,
                "content": "Unknown agent type",
                "error_code": EventErrorCode.TASK_UNKNOWN_AGENT_TYPE_ERROR,
                "result": {
                    "success": False,
                    "error": f"Unknown agent type: {subagent_type}",
                    "available_agents": list(self.available_agents.keys()),
                },
                "final": True,
                "sub_invocation_id": task_id,  # 未知agent类型错误时使用传入的task_id
            }
            return

        # 创建任务ID和执行跟踪
        # task_id = str(uuid.uuid4()) FIXME 其他模型会不会有问题
        task_execution = TaskExecution(task_id, description, subagent_type)
        self.active_tasks[task_id] = task_execution

        try:
            # 发送任务初始化事件
            yield {
                "type": EventType.TASK_START,
                "task_id": task_id,
                "agent_type": subagent_type,
                "description": description,
                "timestamp": time.time(),
                "final": False,
                "sub_invocation_id": task_id,
            }

            task_execution.update_status("running")

            # 创建子代理，传递会话上下文
            context = {}
            if user_id:
                context["user_id"] = user_id
            if session_id:
                context["session_id"] = session_id
            if invocation_id:
                context["invocation_id"] = invocation_id
            if trace:
                context["trace"] = trace
            # 传递task_id作为sub_invocation_id，方便分组subagent的消息列表
            context["sub_invocation_id"] = task_id

            sub_agent = self._create_sub_agent(
                subagent_type, prompt, task_id, parent_span_id, **context
            )
            task_execution.sub_agent = sub_agent
            logger.info(
                f"[{session_id}] [{invocation_id}] Tool {self.name} Sub-agent created successfully, agent: {subagent_type}"
            )

            # 追踪Sub Agent执行
            response_content = None
            start_time = time.time()
            async for chunk in sub_agent.execute(
                session=session,
                session_service=session_service,
                parent_span_id=parent_span_id,
            ):
                # 检查是否是sub_agent的完成事件
                if chunk.get("type") == EventType.COMPLETE_RESPONSE:
                    # 对于完成事件，确保不标记为final，因为task工具还需要继续处理
                    modified_chunk = {**chunk}
                    modified_chunk["sub_invocation_id"] = task_id
                    if modified_chunk.get("is_final") is True:
                        modified_chunk["is_final"] = False
                    yield modified_chunk
                    response_content = extract_message_content(
                        chunk.get("content", "[]")
                    )
                    break
                else:
                    # 确保所有事件都有正确的sub_invocation_id
                    if (
                        "sub_invocation_id" not in chunk
                        or chunk.get("sub_invocation_id") is None
                    ):
                        chunk["sub_invocation_id"] = task_id
                    yield chunk
            duration = time.time() - start_time

            logger.info(
                f"[{session_id}] [{invocation_id}]"
                f"{'->[' + str(sub_agent.sub_invocation_id) + ']' if sub_agent.sub_invocation_id is not None else ''} "
                f"Tool {self.name} Execution complete, starting to collect results, "
                f"Total content length={len(response_content)}"
            )

            # 构造最终结果
            result = {
                "success": True,
                "task_id": task_id,
                "agent_type": subagent_type,
                "task_description": description,
                "agent_description": self.available_agents[subagent_type],
                "result": response_content,
                "duration": duration,
                "context": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "invocation_id": invocation_id,
                    "trace_id": trace.id if trace else None,
                },
                "sub_invocation_id": task_id,
            }

            task_execution.update_status("completed", result=result)

            yield {
                "type": EventType.TASK_COMPLETE,
                "result": result,
                "final": True,
                "sub_invocation_id": task_id,
            }

        except Exception as e:
            error_msg = str(e)
            duration = task_execution.get_duration()
            task_execution.update_status("error", error=error_msg)

            # 记录错误信息
            logger.error(
                f"[{session_id}] [{invocation_id}] Tool {self.name} Execution failed: {error_msg}"
            )

            yield {
                "type": EventType.TASK_ERROR,
                "content": error_msg,
                "error_code": EventErrorCode.TASK_EXECUTION_ERROR,
                "result": {
                    "success": False,
                    "error": error_msg,
                    "task_id": task_id,
                    "agent_type": subagent_type,
                    "duration": duration,
                },
                "final": True,
                "sub_invocation_id": task_id,  # 执行错误时使用task_id
            }

        finally:
            # 延迟清理任务记录
            if task_id in self.active_tasks:
                asyncio.create_task(self._cleanup_task_later(task_id))

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id not in self.active_tasks:
            return None

        task = self.active_tasks[task_id]
        return {
            "task_id": task.task_id,
            "description": task.description,
            "subagent_type": task.subagent_type,
            "status": task.status,
            "start_time": task.start_time,
            "end_time": task.end_time,
            "duration": task.get_duration(),
            "progress_events": task.progress_events,
            "result": task.result,
            "error": task.error,
            "sub_invocation_id": task_id,
        }

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """获取所有活跃任务"""
        return [self.get_task_status(task_id) for task_id in self.active_tasks.keys()]

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id not in self.active_tasks:
            return False

        task = self.active_tasks[task_id]
        if task.status in ["completed", "error", "cancelled"]:
            return False

        task.update_status("cancelled")

        # 如果有子代理，尝试停止它
        # 注意：这里需要根据具体的子代理实现来处理中断
        # 大多数情况下，AsyncGenerator会在外部循环中断时自动停止

        return True

    def clear_completed_tasks(self) -> int:
        """清理已完成的任务，返回清理的数量"""
        completed_task_ids = []
        for task_id, task in self.active_tasks.items():
            if task.status in ["completed", "error", "cancelled"]:
                completed_task_ids.append(task_id)

        for task_id in completed_task_ids:
            del self.active_tasks[task_id]

        return len(completed_task_ids)

    def get_agent_types(self) -> Dict[str, str]:
        """获取所有可用的代理类型和描述"""
        return self.available_agents.copy()
