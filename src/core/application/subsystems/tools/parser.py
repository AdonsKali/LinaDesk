import json
import logging
import re
from typing import Optional, Union
from src.core.application.ports.llm_port import ChatResponse
from src.core.domain.value_objects.tool import ToolCall
from src.core.domain.domain_error import ValidationError

logger = logging.getLogger(__name__)

_TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*(\{.*?\})\s*</tool_call>",
    re.DOTALL,
)

_GEMMA4_TOOL_CALL_RE = re.compile(
    r"<\|tool_call>\s*call:(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\{(?P<args>.*?)\}\s*<tool_call\|>",
    re.DOTALL,
)
_GEMMA4_STR_DELIM = '<|"|>'


class ToolCallParser:
    """
    Парсит tool_calls из ответа LLM.
    Поддерживает нативный формат (ChatResponse.tool_calls) и текстовый.
    """

    def parse_from_response(
        self,
        response: Union[ChatResponse, str],
    ) -> list[ToolCall]:
        if isinstance(response, ChatResponse):
            if response.tool_calls:
                return self._parse_native(response.tool_calls)
            return self.parse_many(response.content or "")
        return self.parse_many(str(response))

    def extract_text(self, response: Union[ChatResponse, str]) -> str:
        content = response.content if isinstance(response, ChatResponse) else str(response)
        content = content or ""

        content = _TOOL_CALL_RE.sub("", content)
        content = re.sub(r"<\|tool_call>.*?<tool_call\|>", "", content, flags=re.DOTALL)
        content = re.sub(r"<\|channel>.*?<channel\|>", "", content, flags=re.DOTALL)
        return content.strip()

    def parse_one(self, text: str) -> Optional[ToolCall]:
        calls = self.parse_many(text)
        return calls[0] if calls else None

    def parse_many(self, text: str) -> list[ToolCall]:
        results: list[ToolCall] = []
        for match in _TOOL_CALL_RE.finditer(text):
            raw = match.group(1)
            call = self._parse_json_call(raw)
            if call is not None:
                results.append(call)
        return results

    def contains_tool_call(self, text: str) -> bool:
        if _TOOL_CALL_RE.search(text):
            return True
        return bool(re.search(r"<\|tool_call>", text))

    def _parse_native(self, tool_calls: list[dict]) -> list[ToolCall]:
        results: list[ToolCall] = []
        if not isinstance(tool_calls, list):
            return results

        for tc in tool_calls:
            if not isinstance(tc, dict):
                continue
            fn = tc.get("function")
            if not isinstance(fn, dict):
                continue
            name = fn.get("name")
            if not name:
                continue

            args_raw = fn.get("arguments", "{}")
            if isinstance(args_raw, str):
                try:
                    args = json.loads(args_raw) if args_raw.strip() else {}
                except json.JSONDecodeError:
                    args = {}
            elif isinstance(args_raw, dict):
                args = args_raw
            else:
                args = {}

            results.append(ToolCall(name=name, arguments=args))

        return results

    def _parse_json_call(self, raw: str) -> Optional[ToolCall]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid tool_call JSON: {e}") from e

        if not isinstance(data, dict) or "name" not in data:
            raise ValidationError("tool_call must be an object with 'name'")

        args = data.get("arguments", {})
        if not isinstance(args, dict):
            raise ValidationError("tool_call 'arguments' must be an object")

        return ToolCall(name=data["name"], arguments=args)



    def parse_gemma4_native(self, text: str) -> list[ToolCall]:
        """Парсит Gemma 4 native `<|tool_call>call:name{...}<tool_call|>`."""
        results = []
        for m in _GEMMA4_TOOL_CALL_RE.finditer(text):
            name = m.group("name")
            args = self._parse_gemma4_args(m.group("args"))
            results.append(ToolCall(name=name, arguments=args))
        return results

    def _parse_gemma4_args(self, args_str: str) -> dict:
        """Парсит `param:<|"|>value<|"|>, param2:<|"|>value2<|"|>`."""
        out = {}
        pos = 0
        while pos < len(args_str):
            m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", args_str[pos:])
            if not m:
                break
            key = m.group(1)
            pos += m.end()
            value, pos = self._parse_gemma4_value(args_str, pos)
            out[key] = value
            sep = re.match(r"\s*,\s*", args_str[pos:])
            pos += sep.end() if sep else 0
        return out

    def _parse_gemma4_value(self, s: str, pos: int):
        """Парсит одно значение."""
        while pos < len(s) and s[pos].isspace():
            pos += 1

        if s.startswith(_GEMMA4_STR_DELIM, pos):
            start = pos + len(_GEMMA4_STR_DELIM)
            end = s.find(_GEMMA4_STR_DELIM, start)
            if end < 0:
                return s[start:], len(s)
            return s[start:end], end + len(_GEMMA4_STR_DELIM)

        # Числа, булевы, etc.
        start = pos
        while pos < len(s) and s[pos] not in ",}]":
            pos += 1
        raw = s[start:pos].strip()

        if raw == "true":
            return True, pos
        if raw == "false":
            return False, pos
        if raw == "null":
            return None, pos
        try:
            if "." in raw:
                return float(raw), pos
            return int(raw), pos
        except ValueError:
            return raw, pos