import os
import time
import json
from typing import Any, Dict, List, Optional
import httpx
from app.adapters.llm.base_provider import BaseLlmProvider, LlmMessage, LlmResponse
from app.tracing.sanitizer import sanitize_text

class OpenAiCompatibleProvider(BaseLlmProvider):
    """
    OpenAI-compatible chat completion provider.
    Supports standard OpenAI API, Azure OpenAI, Ollama, vLLM, LocalAI, and compatible gateways.
    """

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        secret_env_var: Optional[str] = "OPENAI_API_KEY",
        max_retries: int = 2,
        backoff_factor: float = 1.5,
        mock_responses: Optional[List[Dict[str, Any]]] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.secret_env_var = secret_env_var
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.mock_responses = list(mock_responses or [])
        self._mock_call_index = 0

    def get_api_key(self) -> Optional[str]:
        if self.secret_env_var:
            return os.environ.get(self.secret_env_var)
        return None

    def test_connection(self) -> Dict[str, Any]:
        """Validates credentials and endpoint reachability."""
        if self.mock_responses:
            return {
                "status": "healthy",
                "provider": "openai_compatible",
                "model": self.model,
                "base_url": self.base_url,
                "mode": "mock_test_mode",
                "message": "Mock provider operational for deterministic testing."
            }

        api_key = self.get_api_key()
        if not api_key:
            return {
                "status": "unconfigured",
                "provider": "openai_compatible",
                "model": self.model,
                "base_url": self.base_url,
                "secret_env_var": self.secret_env_var,
                "message": f"Environment variable '{self.secret_env_var}' is not set. Please set this variable with your API key to enable live model execution."
            }

        # Probe /models endpoint for quick connectivity check
        url = f"{self.base_url}/models"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "AgentGuard-LlmProvider/1.0"
        }
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code in (200, 201):
                    return {
                        "status": "healthy",
                        "provider": "openai_compatible",
                        "model": self.model,
                        "base_url": self.base_url,
                        "message": f"Successfully connected to {self.base_url} (HTTP {resp.status_code})."
                    }
                elif resp.status_code == 401:
                    return {
                        "status": "error",
                        "provider": "openai_compatible",
                        "message": f"Authentication failed: Invalid API key in environment variable '{self.secret_env_var}'."
                    }
                else:
                    return {
                        "status": "warning",
                        "provider": "openai_compatible",
                        "message": f"Connected to {self.base_url} but /models returned HTTP {resp.status_code}."
                    }
        except Exception as e:
            err = self._sanitize_error(str(e))
            return {
                "status": "error",
                "provider": "openai_compatible",
                "message": f"Failed to reach model endpoint: {err}"
            }

    def chat_complete(
        self,
        messages: List[LlmMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: float = 30.0
    ) -> LlmResponse:
        """Calls /v1/chat/completions with retry logic or returns simulated mock response."""
        # Check mock test responses
        if self.mock_responses:
            if self._mock_call_index < len(self.mock_responses):
                mock_data = self.mock_responses[self._mock_call_index]
                self._mock_call_index += 1
            else:
                mock_data = self.mock_responses[-1]

            return LlmResponse(
                content=mock_data.get("content"),
                tool_calls=mock_data.get("tool_calls", []),
                finish_reason=mock_data.get("finish_reason", "stop"),
                model=self.model,
                prompt_tokens=mock_data.get("prompt_tokens", 50),
                completion_tokens=mock_data.get("completion_tokens", 30),
                total_tokens=mock_data.get("total_tokens", 80),
                raw_response=mock_data
            )

        api_key = self.get_api_key()
        if not api_key:
            raise ValueError(
                f"Cannot execute model request: Environment variable '{self.secret_env_var}' is not configured."
            )

        # Build payload
        payload_messages = []
        for msg in messages:
            m_dict: Dict[str, Any] = {"role": msg.role}
            if msg.content is not None:
                m_dict["content"] = msg.content
            if msg.tool_calls:
                m_dict["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                m_dict["tool_call_id"] = msg.tool_call_id
            if msg.name:
                m_dict["name"] = msg.name
            payload_messages.append(m_dict)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AgentGuard-LlmProvider/1.0"
        }

        url = f"{self.base_url}/chat/completions"
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(url, json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        choice = data.get("choices", [{}])[0]
                        msg = choice.get("message", {})
                        usage = data.get("usage", {})
                        return LlmResponse(
                            content=msg.get("content"),
                            tool_calls=msg.get("tool_calls") or [],
                            finish_reason=choice.get("finish_reason", "stop"),
                            model=data.get("model", self.model),
                            prompt_tokens=usage.get("prompt_tokens", 0),
                            completion_tokens=usage.get("completion_tokens", 0),
                            total_tokens=usage.get("total_tokens", 0),
                            raw_response=data
                        )
                    elif resp.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                        time.sleep(self.backoff_factor ** attempt)
                        continue
                    else:
                        resp_body = resp.text[:500]
                        clean_err = self._sanitize_error(resp_body)
                        raise RuntimeError(f"HTTP {resp.status_code} from model provider: {clean_err}")
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.backoff_factor ** attempt)
                    continue

        clean_last = self._sanitize_error(str(last_error))
        raise RuntimeError(f"Chat completion failed after {self.max_retries + 1} attempts: {clean_last}")

    def _sanitize_error(self, text: str) -> str:
        s = sanitize_text(text)
        api_key = self.get_api_key()
        if api_key and len(api_key) > 4:
            s = s.replace(api_key, "[REDACTED_API_KEY]")
        return s
