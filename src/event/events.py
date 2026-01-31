"""
Event System for the app.
Each user message, model response, tool response, and subagent interaction generates events.
"""

class EventType:
    """Event types for the app."""

    # agent
    RESPONSE_CHUNK = "response_chunk"
    COMPLETE_RESPONSE = "complete_response"
    USER_MESSAGE = "user_message"
    TOOL_CALL = "tool_call"

    # tool
    TOOL_RESPONSE = "tool_response"

    # error
    ERROR = "error"