from litellm import acompletion
from dotenv import load_dotenv
import os
from ...event.events import EventType
import json
from typing import List, Tuple, Dict, Any, AsyncGenerator
from ...tool import execute_tool
import asyncio

load_dotenv()

class FunctionCall:
    def __init__(self, name="", arguments=""):
        self.name = name
        self.arguments = arguments

    def to_dict(self):
        return {"name": self.name, "arguments": self.arguments}

class ToolCall:
    def __init__(self, id="", type="",name="", arguments=""):
        self.id = id
        self.type = type
        self.function = FunctionCall(name=name, arguments=arguments)

    def to_dict(self):
        return {"id": self.id, "type": self.type, "function": self.function.to_dict()}

class ToolCallMessage:
    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []

class ToolCallChoice:
    def __init__(self, content="", tool_calls=None):
        self.message = ToolCallMessage(content=content, tool_calls=tool_calls)

class ToolCallResponse:
    def __init__(self, content="", tool_calls=None):
        self.choices = [ToolCallChoice(content=content, tool_calls=tool_calls)]

async def handle_tool_call_streaming(
    response,
):
    """
    Handle tool call streaming
    """
    if not hasattr(response, "choices") or not response.choices: 
        return 
    
    choice = response.choices[0]
    if not hasattr(choice.message, "tool_calls") or not choice.message.tool_calls:
        return
    
    tool_runs = []
    for tool_call in choice.message.tool_calls:
        tool_call_id = getattr(tool_call, "id", f"tool_{len(tool_runs)}")
        # produce single tool call streaming generator
        generator = execute_single_tool_streaming(tool_call)
        tool_runs.append((tool_call_id, generator))
    
    # merge tool calls run
    async for event in merge_tool_calls_run(tool_runs):
        if isinstance(event, dict) and "tool_call_id" not in event:
            event["tool_call_id"] = "unknown"
        yield event

async def execute_single_tool_streaming(
    tool_call: ToolCall,
):
    """
    Execute single tool call streaming
    """
    function_id = tool_call.id
    function_name = tool_call.function.name
    function_arguments = json.loads(tool_call.function.arguments)

    try:
        result = None 

        result = await execute_tool(function_name, **function_arguments)  # todo: execute_tool

        yield {
            "type": EventType.TOOL_RESPONSE,
            "success": True,
            "tool_call_id": function_id,
            "function_name": function_name,
            "result": result,
        }
    except Exception as e:
        yield {
            "type": EventType.ERROR,
            "success": False,
            "error": str(e),
            "tool_call_id": function_id,
            "function_name": function_name,
        }
        return


async def merge_tool_calls_run(
    tool_runs: List[Tuple[str, object]],
):
    """
    Merge tool calls run
    """
    if not tool_runs:
        return

    # tool call generators
    generators = [tool_run[1]for tool_run in tool_runs]

    tasks = [asyncio.create_task(generator.__anext__()) for generator in generators]
    pending_tasks = set(tasks)

    while pending_tasks:
        done, pending_tasks = await asyncio.wait(pending_tasks, return_when=asyncio.FIRST_COMPLETED)

        for task in done:
            try:
                event = task.result()
                yield event

                # 继续处理下一步
                for i, original_task in enumerate(tasks):
                    if task == original_task:
                        new_task = asyncio.create_task(generators[i].__anext__())
                        tasks[i] = new_task
                        pending_tasks.add(new_task)
                        break

            except StopAsyncIteration:
                # 该生成器已经完成
                continue
            except Exception as e:
                # 该生成器发生异常
                yield {
                    "type": EventType.ERROR,
                    "success": False,
                    "error": str(e),
                }
                continue

def _get(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)

async def handle_recursive_completion(
    messages,
    tools=None,
    model="dashscope/qwen-max-latest",
    thinking=None,
    safety=None,
    session=None,
    session_service=None,
    invocation_id=None,
    author="main_agent",
):
    api_base_url = os.getenv("DASHSCOPE_BASE_URL")

    try:
        completion_params = {
            "model": model,
            "messages": messages,
            "api_base": api_base_url,
            "stream": True,
        }
        if tools:
            completion_params["tools"] = tools
            print("completion_params: ", json.dumps(completion_params, indent=2, ensure_ascii=False))

        response = await acompletion(**completion_params)

        full_content = ""
        tool_calls_dict = {}  # Accumulate tool calls by index

        async for chunk in response:
            print("="*100)
            print("chunck: ", json.dumps(chunk.model_dump(), indent=2, ensure_ascii=False))
            print("="*100)
            choices = _get(chunk, "choices", [])
            if not choices:
                continue

            choice0 = choices[0]
            delta = _get(choice0, "delta", None)
            delta_tool_calls = getattr(delta, "tool_calls", None)
            finish_reason = _get(choice0, "finish_reason", None)

            content = _get(delta, "content", None) if delta is not None else None
            if content:
                full_content += content
                yield {
                    "type": EventType.RESPONSE_CHUNK,
                    "content": content,   # ✅ 这里要发增量内容
                    "author": author,
                    "invocation_id": invocation_id,
                    "model": model,
                }
            
            # Handle tool calls (they accumulate across chunks)   
            if delta_tool_calls:
                # Emit response_chunk event when tool calls are detected
                # yield {
                #     "type": EventType.TOOL_CALL,
                #     "content": "",
                #     "author": author,
                #     "event_id": "",
                #     "model": model,
                #     "sub_invocation_id": "",
                # }

                for tool_call in delta_tool_calls:
                    index = getattr(tool_call, "index", 0)
                    if index not in tool_calls_dict:
                        tool_calls_dict[index] = {
                            "id": getattr(tool_call, "id", ""),
                            "type": getattr(
                                tool_call, "type", "function"
                            ),
                            "function": {
                                "name": "",
                                "arguments": "",
                            },
                        }

                    # Accumulate tool call data
                    if hasattr(tool_call, "id") and tool_call.id:
                        tool_calls_dict[index]["id"] = tool_call.id

                    if (
                        hasattr(tool_call, "function")
                        and tool_call.function
                    ):
                        if (
                            hasattr(tool_call.function, "name")
                            and tool_call.function.name
                        ):
                            tool_calls_dict[index]["function"][
                                "name"
                            ] += tool_call.function.name
                        if (
                            hasattr(tool_call.function, "arguments")
                            and tool_call.function.arguments
                        ):
                            tool_calls_dict[index]["function"][
                                "arguments"
                            ] += tool_call.function.arguments

            # ✅ finish_reason 必须在 delta 外面检查
            if finish_reason:
                print("="*100)
                print("tool_calls_dict: ", json.dumps(tool_calls_dict, indent=2, ensure_ascii=False))
                print("="*100)
                if finish_reason == "stop":
                    yield {
                        "type": EventType.COMPLETE_RESPONSE,
                        "content": full_content,
                        "author": author,
                        "invocation_id": invocation_id,
                        "model": model,
                    }
                    break
                elif finish_reason == "tool_calls":
                    print(json.dumps(chunk.model_dump(), indent=2, ensure_ascii=False))
                    # yield {
                    #     "type": EventType.TOOL_CALL,
                    #     "content": full_content,
                    #     "author": author,
                    #     "invocation_id": invocation_id,
                    #     "model": model,
                    # }
                    # break

        ## handle tool calls
        tool_calls = None
        if tool_calls_dict:
            tool_calls = []
            for index in sorted(tool_calls_dict.keys()):
                tool_call_data = tool_calls_dict[index]
                tool_calls.append(
                    ToolCall(
                        id=tool_call_data["id"],
                        type=tool_call_data["type"],
                        name=tool_call_data["function"]["name"],
                        arguments=tool_call_data["function"]["arguments"],
                    )
                )
        print("="*100)
        print("tool_calls: ", [tc.to_dict() for tc in tool_calls] if tool_calls else "No tool calls")
        print("="*100)

        if not tool_calls:
            return

        ## call tools

        # Create a resposne object for tool handling compatibility
        tool_response = ToolCallResponse(content=full_content, tool_calls=tool_calls)

        # Execuate tool calls and collect results
        tool_results = []

        print("Here is 303")

        async for tool_event in handle_tool_call_streaming(tool_response):
            yield tool_event

            original_tool_call_ids = [tc.id for tc in tool_calls]
            event_tool_call_id = tool_event.get("tool_call_id", "")

            if (tool_event.get("type") == EventType.TOOL_RESPONSE
            and event_tool_call_id in original_tool_call_ids):
                tool_result = {
                    "tool_call_id": event_tool_call_id,
                    "function_name": tool_event.get("function_name", ""),
                    "result": tool_event.get("result", {"success": tool_event.get("success", False)}),
                }
                tool_results.append(tool_result)

        print("Here is 320")

        # if tool_calls:
        #     tool_results = {"weather" : "sunny and warm"}

        assistant_message = {"role": "assistant", "content": full_content}
        if tool_calls:
            api_tool_calls = []
            for tc in tool_calls:
                api_tool_calls.append(
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                )
        assistant_message["tool_calls"] = api_tool_calls
        messages.append(assistant_message)
        print("="*100)
        print("assistant_message: ", json.dumps(assistant_message, indent=2, ensure_ascii=False))
        print("="*100)

        if tool_results:
            for tool_result in tool_results:
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_result["tool_call_id"],
                    "content": json.dumps(tool_result["result"], indent=2, ensure_ascii=False),
                }
                messages.append(tool_message)

        print("*"*100)
        print("messages: ", json.dumps(messages, indent=2, ensure_ascii=False))
        print("*"*100)
        async for chunk in handle_recursive_completion(
                messages=messages,
                tools=tools,
                model=model,
            ):
                yield chunk

    except Exception as e:
        yield {
            "type": EventType.ERROR,
            "content": f"{type(e).__name__}: {e}",
            "author": author,
            "invocation_id": invocation_id,
            "model": model,
        }

