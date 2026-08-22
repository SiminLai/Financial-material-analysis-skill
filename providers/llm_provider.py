import os
import requests
import json
import time
import random

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
        self._use_stub = False
        if not self.api_key:
            # allow running in offline/demo mode with a stub provider
            print("Warning: DEEPSEEK_API_KEY not set — using local stub LLM responses.")
            self._use_stub = True

    def _post(self, payload: dict) -> dict:
        """
        Send a POST request to the DeepSeek API.
        """
        # configurable retry / timeout
        retries = int(os.getenv("DEEPSEEK_RETRIES", "3"))
        timeout = float(os.getenv("DEEPSEEK_TIMEOUT", "60"))
        backoff_base = float(os.getenv("DEEPSEEK_BACKOFF_BASE", "1"))

        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=timeout,
                )

                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                last_exc = e
                wait = backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 1)
                print(f"LLM request failed (attempt {attempt}/{retries}): {e}. Retrying in {wait:.1f}s...")
                time.sleep(wait)

        # exhausted retries
        raise last_exc

    def _request(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful financial analyst.",
        reasoning_effort: str | None = None,
        **kwargs,
    ) -> str:
        if self._use_stub:
            # Metric extractor specific stub
            if 'You are a STRICT financial extraction system' in prompt:
                stub = {
                    "company_name": "",
                    "revenue": None,
                    "net_profit": None,
                    "debt_ratio": None,
                    "cash_flow": None
                }
                return json.dumps(stub)

            # Report generator / strict reporting stub
            if 'Provide a JSON report' in prompt or 'STRICT financial reporting' in prompt or 'OUTPUT FORMAT' in prompt:
                stub = {
                    "summary": "(stub) No LLM available — summary skipped.",
                    "risk_assessment": "(stub)",
                    "recommendation": "HOLD",
                    "key_points": [],
                    "external_evidence": {},
                    "meta": {}
                }
                return json.dumps(stub)

            # default stub: short text
            return "(stub) LLM not available."

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
