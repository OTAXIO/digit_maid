"""Parser for the small, data-only YAML subset used by Digit Maid."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


class RestrictedYamlError(ValueError):
    """Raised when configuration uses syntax outside the supported subset."""


@dataclass(frozen=True)
class _Token:
    indent: int
    content: str
    line_number: int


_INTEGER = re.compile(r"[-+]?\d+")
_FLOAT = re.compile(r"[-+]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][-+]?\d+)?")
_FORBIDDEN_KEY_CHARS = frozenset("!&*{}[]|>%@`")
_FORBIDDEN_SCALAR_PREFIXES = ("!", "&", "*", "{", "[", "|", ">", "%", "---", "...")


def load_restricted_mapping(text: str) -> dict[str, Any]:
    """Load mappings, scalar values and scalar lists without YAML extensions.

    The project configuration does not need aliases, tags, flow collections,
    multiline strings or object construction, so those features are rejected.
    """

    tokens = _tokenize(text)
    if not tokens:
        return {}
    if tokens[0].indent != 0:
        raise RestrictedYamlError(f"第 {tokens[0].line_number} 行：顶层不能缩进")

    payload, position = _parse_block(tokens, 0, 0)
    if position != len(tokens):
        token = tokens[position]
        raise RestrictedYamlError(f"第 {token.line_number} 行：缩进层级无效")
    if not isinstance(payload, dict):
        raise RestrictedYamlError("配置顶层必须是映射")
    return payload


def _tokenize(text: str) -> list[_Token]:
    tokens: list[_Token] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if "\x00" in raw_line:
            raise RestrictedYamlError(f"第 {line_number} 行：包含空字符")
        content = raw_line.lstrip(" ")
        if not content or content.startswith("#"):
            continue
        if content.startswith("-") and content != "-" and not content.startswith("- "):
            raise RestrictedYamlError(
                f"第 {line_number} 行：列表短横线后必须有空格（应写成 '- 内容'）"
            )
        indent_text = raw_line[: len(raw_line) - len(content)]
        if "\t" in indent_text:
            raise RestrictedYamlError(f"第 {line_number} 行：不能使用 Tab 缩进")
        tokens.append(_Token(len(indent_text), content.rstrip(), line_number))
    return tokens


def _parse_block(tokens: list[_Token], position: int, indent: int) -> tuple[Any, int]:
    is_list = tokens[position].content == "-" or tokens[position].content.startswith("- ")
    container: Any = [] if is_list else {}

    while position < len(tokens):
        token = tokens[position]
        if token.indent < indent:
            break
        if token.indent > indent:
            raise RestrictedYamlError(f"第 {token.line_number} 行：出现意外缩进")

        item_is_list = token.content == "-" or token.content.startswith("- ")
        if item_is_list != is_list:
            raise RestrictedYamlError(f"第 {token.line_number} 行：不能混用列表和映射")

        if is_list:
            raw_value = token.content[1:].strip()
            if not raw_value:
                raise RestrictedYamlError(f"第 {token.line_number} 行：列表项不能为空")
            container.append(_parse_scalar(raw_value, token.line_number))
            position += 1
            continue

        key, raw_value = _split_mapping(token)
        position += 1
        if raw_value:
            container[key] = _parse_scalar(raw_value, token.line_number)
            continue

        if position < len(tokens) and tokens[position].indent > indent:
            child_indent = tokens[position].indent
            container[key], position = _parse_block(tokens, position, child_indent)
        else:
            container[key] = {}

    return container, position


def _split_mapping(token: _Token) -> tuple[str, str]:
    if ":" not in token.content:
        raise RestrictedYamlError(f"第 {token.line_number} 行：映射项缺少冒号")
    raw_key, raw_value = token.content.split(":", 1)
    key = raw_key.strip()
    if (
        not key
        or len(key) > 256
        or any(character in _FORBIDDEN_KEY_CHARS or ord(character) < 32 for character in key)
    ):
        raise RestrictedYamlError(f"第 {token.line_number} 行：键名无效")
    return key, raw_value.strip()


def _parse_scalar(raw_value: str, line_number: int) -> Any:
    if raw_value == "[]":
        return []
    if raw_value == "{}":
        return {}

    if raw_value.startswith('"'):
        try:
            value = json.loads(raw_value)
        except (json.JSONDecodeError, TypeError) as exc:
            raise RestrictedYamlError(f"第 {line_number} 行：双引号字符串无效") from exc
        if not isinstance(value, str):
            raise RestrictedYamlError(f"第 {line_number} 行：只允许字符串标量")
        return value

    if raw_value.startswith("'"):
        if len(raw_value) < 2 or not raw_value.endswith("'"):
            raise RestrictedYamlError(f"第 {line_number} 行：单引号字符串无效")
        return raw_value[1:-1].replace("''", "'")

    if raw_value.startswith(_FORBIDDEN_SCALAR_PREFIXES):
        raise RestrictedYamlError(f"第 {line_number} 行：不支持 YAML 标签、引用或复杂值")

    normalized = raw_value.casefold()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    if normalized in {"null", "~"}:
        return None
    if _INTEGER.fullmatch(raw_value):
        return int(raw_value)
    if _FLOAT.fullmatch(raw_value):
        return float(raw_value)
    return raw_value
