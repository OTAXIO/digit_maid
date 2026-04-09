from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QSettings


DEFAULT_CONTEXT_ROUNDS = 5


@dataclass(frozen=True)
class ProviderPreset:
    name: str
    base_url: str
    default_model: str


@dataclass
class AIConfig:
    provider: str
    api_key: str
    base_url: str
    model: str
    context_rounds: int = DEFAULT_CONTEXT_ROUNDS


PROVIDER_PRESETS: tuple[ProviderPreset, ...] = (
    ProviderPreset("DeepSeek", "https://api.deepseek.com", "deepseek-chat"),
    ProviderPreset("OpenAI", "https://api.openai.com/v1", "gpt-4o-mini"),
    ProviderPreset("Qwen", "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
    ProviderPreset("Doubao", "https://ark.cn-beijing.volces.com/api/v3", "doubao-1.5-pro-32k"),
    ProviderPreset("Gemini", "https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.0-flash"),
)


class AISettingsService:
    def __init__(self, org_name: str = "DigitMaid", app_name: str = "DigitMaid"):
        self.settings = QSettings(org_name, app_name)

    @property
    def provider_presets(self) -> tuple[ProviderPreset, ...]:
        return PROVIDER_PRESETS

    def provider_names(self) -> list[str]:
        return [preset.name for preset in PROVIDER_PRESETS]

    def get_preset_by_name(self, provider_name: str) -> ProviderPreset | None:
        for preset in PROVIDER_PRESETS:
            if preset.name == provider_name:
                return preset
        return None

    def default_config(self) -> AIConfig:
        preset = PROVIDER_PRESETS[0]
        return AIConfig(
            provider=preset.name,
            api_key="",
            base_url=preset.base_url,
            model=preset.default_model,
            context_rounds=DEFAULT_CONTEXT_ROUNDS,
        )

    def load_config(self) -> AIConfig:
        default = self.default_config()

        provider = str(self.settings.value("ai/provider", default.provider) or default.provider).strip()
        base_url = str(self.settings.value("ai/base_url", "") or "").strip()
        model = str(self.settings.value("ai/model", "") or "").strip()
        api_key = str(self.settings.value("ai/api_key", "") or "").strip()
        context_rounds = self._safe_context_rounds(self.settings.value("ai/context_rounds", default.context_rounds))

        preset = self.get_preset_by_name(provider)
        if not base_url:
            base_url = preset.base_url if preset else default.base_url
        if not model:
            model = preset.default_model if preset else default.model

        if not provider:
            provider = default.provider

        return AIConfig(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            model=model,
            context_rounds=context_rounds,
        )

    def save_config(self, config: AIConfig):
        self.settings.setValue("ai/provider", config.provider)
        self.settings.setValue("ai/api_key", config.api_key)
        self.settings.setValue("ai/base_url", config.base_url)
        self.settings.setValue("ai/model", config.model)
        self.settings.setValue("ai/context_rounds", int(max(1, config.context_rounds)))
        self.settings.sync()

    def has_api_key(self) -> bool:
        key = str(self.settings.value("ai/api_key", "") or "").strip()
        return bool(key)

    def is_chat_enabled(self) -> bool:
        value = self.settings.value("ai/enabled", True)
        return self._to_bool(value, True)

    def set_chat_enabled(self, enabled: bool):
        self.settings.setValue("ai/enabled", bool(enabled))
        self.settings.sync()

    @staticmethod
    def _safe_context_rounds(value) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return DEFAULT_CONTEXT_ROUNDS
        return max(1, parsed)

    @staticmethod
    def _to_bool(value, default: bool) -> bool:
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            low = value.strip().lower()
            if low in ("1", "true", "yes", "on"):
                return True
            if low in ("0", "false", "no", "off"):
                return False

        try:
            return bool(int(value))
        except (TypeError, ValueError):
            return bool(default)
