from __future__ import annotations

import json
from urllib import error, request

from .config_service import AIConfig


class AIClientError(RuntimeError):
    pass


class OpenAICompatibleClient:
    _MODEL_BY_PROVIDER = {
        "deepseek": "deepseek-chat",
        "openai": "gpt-4o-mini",
        "qwen": "qwen-plus",
        "doubao": "doubao-1.5-pro-32k",
        "gemini": "gemini-2.0-flash",
    }

    def __init__(self, config: AIConfig, timeout_seconds: int = 30):
        self.config = config
        self.timeout_seconds = max(5, int(timeout_seconds))

    def chat(self, messages: list[dict[str, str]]) -> str:
        endpoint = self._build_endpoint()
        model_name = self._resolve_model_name()
        payload = {
            "model": model_name,
            "messages": messages,
        }

        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            raise AIClientError(self._map_http_error(exc.code, body)) from exc
        except error.URLError as exc:
            reason = str(getattr(exc, "reason", exc)).lower()
            if "timed out" in reason:
                raise AIClientError("请求超时，请稍后重试。") from exc
            raise AIClientError("网络连接失败，请检查网络后重试。") from exc
        except TimeoutError as exc:
            raise AIClientError("请求超时，请稍后重试。") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AIClientError("AI 返回内容无法解析，请稍后重试。") from exc

        content = self._extract_content(data)
        if not content:
            raise AIClientError("AI 返回结构异常，请稍后重试。")
        return content

    def _build_endpoint(self) -> str:
        base_url = str(self.config.base_url or "").strip().rstrip("/")
        if not base_url:
            raise AIClientError("AI 服务地址为空，请先完成配置。")
        if not self.config.api_key:
            raise AIClientError("未检测到 API Key，请先完成配置。")
        return f"{base_url}/chat/completions"

    def _resolve_model_name(self) -> str:
        provider = str(getattr(self.config, "provider", "") or "").strip().lower()
        if provider in self._MODEL_BY_PROVIDER:
            return self._MODEL_BY_PROVIDER[provider]

        base_url = str(self.config.base_url or "").strip().lower()
        if "deepseek" in base_url:
            return "deepseek-chat"
        if "dashscope.aliyuncs.com" in base_url:
            return "qwen-plus"
        if "volces.com" in base_url or "ark.cn" in base_url:
            return "doubao-1.5-pro-32k"
        if "generativelanguage.googleapis.com" in base_url:
            return "gemini-2.0-flash"
        if "api.openai.com" in base_url:
            return "gpt-4o-mini"

        # Fallback for unknown OpenAI-compatible providers.
        return "gpt-4o-mini"

    @staticmethod
    def _extract_content(data: dict) -> str:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""

        first = choices[0]
        if not isinstance(first, dict):
            return ""

        message_obj = first.get("message")
        if isinstance(message_obj, dict):
            content = message_obj.get("content")
            if isinstance(content, list):
                chunks = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        chunks.append(str(part.get("text", "")))
                return "\n".join(chunk for chunk in chunks if chunk).strip()
            if content is not None:
                return str(content).strip()

        text = first.get("text")
        if text is not None:
            return str(text).strip()

        return ""

    def _map_http_error(self, status_code: int, body: str) -> str:
        remote_detail = self._extract_remote_error(body)

        if status_code in (401, 403):
            return "鉴权失败，请检查 API Key 是否正确。"
        if status_code == 429:
            return "请求过于频繁或配额不足，请稍后再试。"
        if status_code >= 500:
            return "AI 服务暂时不可用，请稍后再试。"
        if remote_detail:
            return f"请求失败（HTTP {status_code}）：{remote_detail}"
        return f"请求失败（HTTP {status_code}）。"

    @staticmethod
    def _extract_remote_error(body: str) -> str:
        if not body:
            return ""
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            return ""

        if isinstance(parsed, dict):
            error_obj = parsed.get("error")
            if isinstance(error_obj, dict):
                message = error_obj.get("message")
                if message:
                    return str(message)
            message = parsed.get("message")
            if message:
                return str(message)
        return ""
