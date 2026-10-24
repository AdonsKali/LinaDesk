import re
import json
import random
import string
from typing import Tuple, Any, Dict, List, Optional

_GEMMA4_TOOL_CALL_RE = re.compile(
    r"<\|tool_call>\s*call:(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\{(?P<args>.*?)\}\s*<tool_call\|>",
    re.DOTALL,
)
_GEMMA4_THOUGHT_RE = re.compile(r"<\|channel>\s*thought.*?<channel\|>", re.DOTALL)
_GEMMA4_STR_DELIM = '<|"|>'


def _gemma4_parse_value(s: str, pos: int) -> Tuple[Any, int]:
    """Parse a single Gemma 4 value starting at ``s[pos]``.
    Returns ``(value, new_pos)`` where ``new_pos`` points just past the value.
    """
    while pos < len(s) and s[pos].isspace():
        pos += 1
    
    # string literal: <|"|>...<|"|>
    if s.startswith(_GEMMA4_STR_DELIM, pos):
        start = pos + len(_GEMMA4_STR_DELIM)
        end = s.find(_GEMMA4_STR_DELIM, start)
        if end < 0:
            return s[start:], len(s)
        return s[start:end], end + len(_GEMMA4_STR_DELIM)
    
    # list literal: [v1,v2,...]
    if pos < len(s) and s[pos] == "[":
        items: List[Any] = []
        pos += 1
        while pos < len(s):
            while pos < len(s) and s[pos].isspace():
                pos += 1
            if pos < len(s) and s[pos] == "]":
                return items, pos + 1
            val, pos = _gemma4_parse_value(s, pos)
            items.append(val)
            while pos < len(s) and s[pos] in " \t,":
                pos += 1
        return items, pos
    
    # primitive literal: read until separator
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
        if "." in raw or "e" in raw.lower():
            return float(raw), pos
        return int(raw), pos
    except ValueError:
        return raw, pos


def _gemma4_parse_args(args_str: str) -> Dict[str, Any]:
    """Parse the inside of a Gemma 4 ``{...}`` arg block into ``{name: value}``."""
    out: Dict[str, Any] = {}
    pos = 0
    while pos < len(args_str):
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", args_str[pos:])
        if not m:
            break
        key = m.group(1)
        pos += m.end()
        val, pos = _gemma4_parse_value(args_str, pos)
        out[key] = val
        sep = re.match(r"\s*,\s*", args_str[pos:])
        pos += sep.end() if sep else 0
    return out


def parse_gemma4_native_tool_calls(
    text: str,
) -> Tuple[Optional[str], Optional[List[Dict[str, Any]]]]:
    """Extract Gemma 4 native tool-call tokens from a completion.
    Returns ``(content_remainder, tool_calls)``. When no ``<|tool_call>`` token
    is present the original ``text`` is returned with ``tool_calls=None`` so
    plain-text replies pass through unchanged.
    """
    cleaned = _GEMMA4_THOUGHT_RE.sub("", text)
    
    if "<|tool_call>" not in cleaned:
        return text, None
    
    tool_calls: List[Dict[str, Any]] = []
    for i, m in enumerate(_GEMMA4_TOOL_CALL_RE.finditer(cleaned)):
        name = m.group("name")
        args = _gemma4_parse_args(m.group("args"))
        
        suffix = ''.join(random.choices(string.hexdigits.lower()[:16], k=8))
        tool_calls.append(
            {
                "id": f"call_{i}_{name}_{suffix}",
                "type": "function",
                "function": {
                    "name": name, 
                    "arguments": json.dumps(args)
                },
            }
        )
    
    if not tool_calls:
        return text, None
    
    remainder = _GEMMA4_TOOL_CALL_RE.sub("", cleaned).strip()
    return (remainder if remainder else None), tool_calls