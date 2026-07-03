import os
import requests

from providers.base_provider import BaseProvider


class LLMProvider(BaseProvider):
    """
    DeepSeek LLM Provider
    """

    name = "deepseek_llm"

    def __init__(
        self,
        model_name: str = "deepseek-chat",
        api_key: str | None = None,
        base_url: str = "https://api.deepseek.com",
    ):
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")

        # 优先使用传入的 api_key，其次读取环境变量
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")

        if not self.api_key:
            raise ValueError(
                "DeepSeek API key is required.\n"
                "Please provide `api_key` when initializing LLMProvider "
                "or set the environment variable `DEEPSEEK_API_KEY`."
            )

    def _post(self, payload: dict) -> dict:
        """
        Send a POST request to the DeepSeek API.
        """

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )

        response.raise_for_status()

        return response.json()

    def _request(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful financial analyst.",
        reasoning_effort: str | None = None,
        **kwargs,
    ) -> str:

        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "stream": False,
        }

        if reasoning_effort is not None:
            payload["reasoning_effort"] = reasoning_effort

        payload.update(kwargs)

        result = self._post(payload)

        return result["choices"][0]["message"]["content"]
