import logging
import base64
import mimetypes
from typing import TypeVar, Type

from openai import AzureOpenAI
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings


logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AzureOpenAIService:

    def __init__(self) -> None:

        settings = get_settings()

        self.client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version="2025-04-01-preview",
            azure_endpoint=settings.azure_openai_endpoint,
        )

        self.deployment = settings.azure_openai_deployment

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def structured_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
    ) -> T:

        logger.info(
            "Calling Azure OpenAI deployment=%s",
            self.deployment,
        )

        response = self.client.beta.chat.completions.parse(
            model=self.deployment,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            response_format=response_model,
        )

        parsed = response.choices[0].message.parsed

        if parsed is None:
            raise ValueError(
                "Azure OpenAI returned no structured response"
            )

        return parsed

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def vision_structured_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        image_path: str,
        response_model: Type[T],
    ) -> T:
        """Classify image documents with the Azure OpenAI vision interface."""
        mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("ascii")

        response = self.client.beta.chat.completions.parse(
            model=self.deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                        },
                    ],
                },
            ],
            response_format=response_model,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError("Azure OpenAI returned no structured vision response")
        return parsed
