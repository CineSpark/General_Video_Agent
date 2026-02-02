import os
from typing import Optional

import dashscope
from ...logger import logger


class QwenVLM:
    """Qwen VLM model caller class using the official dashscope SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "qwen3-vl-plus",
        base_http_api_url: Optional[str] = None,
    ):
        """Initializes the Qwen VLM model client.

        Args:
            api_key: API key, defaults to DASHSCOPE_API_KEY environment variable.
            model: Name of the model to use.
            base_http_api_url: API base URL for switching regions (e.g., Singapore region).
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.model = model

        if not self.api_key:
            raise ValueError("API key not set. Please set DASHSCOPE_API_KEY")

        if base_http_api_url:
            dashscope.base_http_api_url = base_http_api_url

    def call_model(
        self, media_url: str, prompt: str, media_type: str = "video", fps: float = 2.0
    ) -> str:
        """Calls Qwen VLM model to analyze video or image.

        Args:
            media_url: Public access URL of the media file (video or image).
            prompt: Analysis prompt.
            media_type: Media type, either "video" or "image", defaults to "video".
            fps: Video frame sampling rate, indicating one frame is extracted every 1/fps seconds
                (only valid for video).

        Returns:
            Raw response string from the model.

        Raises:
            ValueError: If unsupported media type is provided.
            Exception: If model call fails.
        """
        if media_type not in ["video", "image"]:
            raise ValueError(
                f"Unsupported media type: {media_type}, only 'video' or 'image' are supported"
            )

        try:
            logger.debug(f"Calling Qwen VLM model: {self.model}")
            logger.debug(f"{media_type.upper()} URL: {media_url}")

            # Build content based on media type
            content = []
            if media_type == "video":
                content.append({"video": media_url, "fps": fps})
            else:  # image
                content.append({"image": media_url})

            content.append({"text": prompt})

            messages = [{"role": "user", "content": content}]

            response = dashscope.MultiModalConversation.call(
                api_key=self.api_key,
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
            )

            if response.status_code == 200:
                result_text = response.output.choices[0].message.content[0]["text"]
                logger.debug(f"Raw model response length: {len(result_text)}")
                return result_text
            else:
                error_msg = (
                    f"Model call failed, status code: {response.status_code}, "
                    f"error message: {response.message}"
                )
                logger.error(error_msg)
                raise Exception(error_msg)

        except Exception as e:
            logger.error(f"Qwen VLM model call failed: {e}")
            raise
