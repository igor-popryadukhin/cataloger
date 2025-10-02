from __future__ import annotations

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from catalog_cli.config import SETTINGS


class DeepSeekError(Exception):
    """Base exception for DeepSeek client."""


class DeepSeekAuthError(DeepSeekError):
    """Raised when authentication fails."""


class DeepSeekTransientError(DeepSeekError):
    """Raised for transient errors that may succeed on retry."""


class DeepSeekClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        max_retries: int = 5,
    ) -> None:
        self.base_url = base_url or SETTINGS.deepseek_base_url
        self.api_key = api_key or SETTINGS.deepseek_api_key
        self.model = model or SETTINGS.deepseek_model
        if not self.api_key:
            raise DeepSeekAuthError("DEEPSEEK_API_KEY is not configured")
        timeout = timeout or SETTINGS.timeout
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)
        self.retrying = AsyncRetrying(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(DeepSeekTransientError),
            reraise=True,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def __aenter__(self) -> "DeepSeekClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def generate(self, prompt: str) -> str:
        async for attempt in self.retrying:
            with attempt:
                return await self._request(prompt)
        raise DeepSeekError("Failed to obtain response from DeepSeek API")

    async def _request(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an assistant that generates service category taxonomies."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = await self.client.post("/chat/completions", json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise DeepSeekTransientError(f"Network error: {exc}") from exc
        if response.status_code == 401:
            raise DeepSeekAuthError("DeepSeek API returned 401 Unauthorized")
        if response.status_code in {429, 500, 502, 503, 504}:
            raise DeepSeekTransientError(f"Transient error {response.status_code}: {response.text}")
        if response.is_error:
            raise DeepSeekError(f"DeepSeek API error {response.status_code}: {response.text}")
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise DeepSeekError(f"Malformed response from DeepSeek API: {data}") from exc
