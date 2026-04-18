from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SUPPORTED_INGESTION_FORMATS: tuple[str, ...] = ("chatgpt_json", "claude_json", "open_webui_json", "markdown")
MARKDOWN_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


class IngestionParseError(ValueError):
    """Raised when an external session export cannot be parsed."""


@dataclass(slots=True)
class ConversationTurn:
    role: str
    content: str
    timestamp: str = ""
    turn_id: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.role = self.role.strip().lower()
        self.content = self.content.strip()
        self.timestamp = self.timestamp.strip()
        self.turn_id = self.turn_id.strip()
        normalized_metadata: dict[str, str] = {}
        for key, value in self.metadata.items():
            normalized_key = str(key).strip()
            normalized_value = str(value).strip()
            if normalized_key and normalized_value:
                normalized_metadata[normalized_key] = normalized_value
        self.metadata = normalized_metadata
        if not self.role:
            raise IngestionParseError("conversation turn role must be a non-empty string")
        if not self.content:
            raise IngestionParseError("conversation turn content must be a non-empty string")


def parse_ingestion_path(path: Path, format_hint: str | None = None) -> list[ConversationTurn]:
    return parse_ingestion_bytes(path.read_bytes(), format_hint=format_hint, source_name=path.name)


def parse_ingestion_bytes(
    data: bytes,
    format_hint: str | None = None,
    source_name: str = "<memory>",
) -> list[ConversationTurn]:
    normalized_hint = (format_hint or "").strip().lower()
    if normalized_hint == "markdown":
        return parse_markdown_text(data.decode("utf-8"), source_name=source_name)

    if normalized_hint and normalized_hint not in SUPPORTED_INGESTION_FORMATS:
        raise IngestionParseError(
            f"Unsupported ingestion format '{format_hint}'. Expected one of: {', '.join(SUPPORTED_INGESTION_FORMATS)}"
        )

    if normalized_hint in {"chatgpt_json", "claude_json", "open_webui_json"}:
        payload = _load_json_payload(data, source_name=source_name)
        return _parse_json_payload(payload, normalized_hint)

    if _looks_like_markdown(data, source_name):
        return parse_markdown_text(data.decode("utf-8"), source_name=source_name)

    payload = _load_json_payload(data, source_name=source_name)
    detected_format = detect_ingestion_format(payload)
    return _parse_json_payload(payload, detected_format)


def detect_ingestion_format(payload: Any) -> str:
    if _is_chatgpt_export(payload):
        return "chatgpt_json"
    if _is_claude_export(payload):
        return "claude_json"
    if _is_open_webui_export(payload):
        return "open_webui_json"
    raise IngestionParseError(
        "Unsupported ingestion payload. Expected ChatGPT JSON, Claude JSON, Open WebUI JSON, or Markdown."
    )


def parse_chatgpt_export(payload: Any) -> list[ConversationTurn]:
    conversations = payload if isinstance(payload, list) else [payload]
    turns: list[tuple[float, int, ConversationTurn]] = []
    sequence = 0
    for conversation in conversations:
        if not isinstance(conversation, dict):
            continue
        mapping = conversation.get("mapping")
        if not isinstance(mapping, dict) or not mapping:
            continue
        title = str(conversation.get("title", "")).strip()
        for node_id, node in mapping.items():
            if not isinstance(node, dict):
                continue
            message = node.get("message")
            if not isinstance(message, dict):
                continue
            role = _extract_chatgpt_role(message)
            content = _extract_chatgpt_content(message)
            if not role or not content:
                continue
            create_time = message.get("create_time")
            turns.append(
                (
                    _as_sortable_timestamp(create_time, sequence),
                    sequence,
                    ConversationTurn(
                        role=role,
                        content=content,
                        timestamp=_stringify_timestamp(create_time),
                        turn_id=str(node_id).strip(),
                        metadata={"conversation_title": title} if title else {},
                    ),
                )
            )
            sequence += 1
    if not turns:
        raise IngestionParseError("ChatGPT export did not contain any parseable messages.")
    turns.sort(key=lambda item: (item[0], item[1]))
    return [turn for _, _, turn in turns]


def parse_claude_export(payload: Any) -> list[ConversationTurn]:
    if not isinstance(payload, dict):
        raise IngestionParseError("Claude export must be a JSON object containing 'chat_messages'.")
    messages = payload.get("chat_messages")
    if not isinstance(messages, list):
        raise IngestionParseError("Claude export is missing 'chat_messages'.")

    turns: list[ConversationTurn] = []
    conversation_name = str(payload.get("name", "")).strip()
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            continue
        role = str(message.get("sender", message.get("role", ""))).strip().lower()
        content = _extract_claude_content(message.get("content"))
        if not role or not content:
            continue
        metadata = {"conversation_name": conversation_name} if conversation_name else {}
        turns.append(
            ConversationTurn(
                role=role,
                content=content,
                timestamp=_stringify_timestamp(message.get("created_at", message.get("updated_at"))),
                turn_id=str(message.get("uuid", message.get("id", index))).strip(),
                metadata=metadata,
            )
        )
    if not turns:
        raise IngestionParseError("Claude export did not contain any parseable chat messages.")
    return turns


def parse_open_webui_export(payload: Any) -> list[ConversationTurn]:
    messages = _extract_open_webui_messages(payload)
    turns: list[ConversationTurn] = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "")).strip().lower()
        content = _extract_open_webui_content(message.get("content"))
        if not role or not content:
            continue
        turns.append(
            ConversationTurn(
                role=role,
                content=content,
                timestamp=_stringify_timestamp(message.get("timestamp", message.get("created_at"))),
                turn_id=str(message.get("id", index)).strip(),
            )
        )
    if not turns:
        raise IngestionParseError("Open WebUI export did not contain any parseable messages.")
    return turns


def parse_markdown_text(text: str, source_name: str = "<memory>") -> list[ConversationTurn]:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        raise IngestionParseError("Markdown ingestion source is empty.")

    headings: list[tuple[str, int, int]] = []
    lines = normalized.split("\n")
    for index, line in enumerate(lines):
        match = MARKDOWN_HEADING_PATTERN.match(line.strip())
        if match:
            headings.append((match.group(2).strip(), len(match.group(1)), index))

    if not headings:
        return [
            ConversationTurn(
                role="document",
                content=normalized,
                metadata={"source_name": source_name},
            )
        ]

    turns: list[ConversationTurn] = []
    for current_index, (heading, level, line_index) in enumerate(headings):
        next_line_index = headings[current_index + 1][2] if current_index + 1 < len(headings) else len(lines)
        body_lines = lines[line_index + 1 : next_line_index]
        body = "\n".join(body_lines).strip()
        content = f"{heading}\n\n{body}".strip() if body else heading
        turns.append(
            ConversationTurn(
                role="document",
                content=content,
                turn_id=f"heading-{current_index + 1}",
                metadata={
                    "heading": heading,
                    "heading_level": str(level),
                    "source_name": source_name,
                },
            )
        )
    return turns


def _parse_json_payload(payload: Any, format_name: str) -> list[ConversationTurn]:
    if format_name == "chatgpt_json":
        return parse_chatgpt_export(payload)
    if format_name == "claude_json":
        return parse_claude_export(payload)
    if format_name == "open_webui_json":
        return parse_open_webui_export(payload)
    raise IngestionParseError(f"Unsupported ingestion format '{format_name}'.")


def _load_json_payload(data: bytes, source_name: str) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise IngestionParseError(f"{source_name} is not valid UTF-8 input.") from exc
    except json.JSONDecodeError as exc:
        raise IngestionParseError(f"{source_name} is not valid JSON or Markdown.") from exc


def _looks_like_markdown(data: bytes, source_name: str) -> bool:
    lowered_name = source_name.lower()
    if lowered_name.endswith((".md", ".markdown")):
        return True
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    stripped = text.lstrip()
    if not stripped:
        return False
    return bool(MARKDOWN_HEADING_PATTERN.search(text)) and not stripped.startswith(("{", "["))


def _is_chatgpt_export(payload: Any) -> bool:
    if isinstance(payload, dict):
        mapping = payload.get("mapping")
        return isinstance(mapping, dict)
    if isinstance(payload, list) and payload:
        first = payload[0]
        return isinstance(first, dict) and isinstance(first.get("mapping"), dict)
    return False


def _is_claude_export(payload: Any) -> bool:
    return isinstance(payload, dict) and isinstance(payload.get("chat_messages"), list)


def _is_open_webui_export(payload: Any) -> bool:
    if isinstance(payload, dict) and isinstance(payload.get("messages"), list):
        return True
    if isinstance(payload, list):
        return all(isinstance(item, dict) and "role" in item for item in payload)
    return False


def _extract_chatgpt_role(message: dict[str, Any]) -> str:
    author = message.get("author")
    if isinstance(author, dict):
        return str(author.get("role", "")).strip().lower()
    return ""


def _extract_chatgpt_content(message: dict[str, Any]) -> str:
    content = message.get("content")
    if not isinstance(content, dict):
        return ""
    content_type = str(content.get("content_type", "")).strip().lower()
    if content_type == "text":
        parts = content.get("parts")
        if isinstance(parts, list):
            return "\n".join(str(part).strip() for part in parts if str(part).strip()).strip()
    if content_type == "multimodal_text":
        parts = content.get("parts")
        if isinstance(parts, list):
            fragments: list[str] = []
            for part in parts:
                if isinstance(part, str) and part.strip():
                    fragments.append(part.strip())
                elif isinstance(part, dict):
                    text = str(part.get("text", "")).strip()
                    if text:
                        fragments.append(text)
            return "\n".join(fragments).strip()
    return ""


def _extract_claude_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    fragments: list[str] = []
    for block in content:
        if isinstance(block, str) and block.strip():
            fragments.append(block.strip())
            continue
        if not isinstance(block, dict):
            continue
        if str(block.get("type", "")).strip().lower() != "text":
            continue
        text = str(block.get("text", "")).strip()
        if text:
            fragments.append(text)
    return "\n".join(fragments).strip()


def _extract_open_webui_messages(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        messages = payload.get("messages")
        if isinstance(messages, list):
            return [item for item in messages if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    raise IngestionParseError("Open WebUI export must contain a top-level 'messages' array.")


def _extract_open_webui_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        fragments: list[str] = []
        for item in content:
            if isinstance(item, str) and item.strip():
                fragments.append(item.strip())
            elif isinstance(item, dict):
                text = str(item.get("text", "")).strip()
                if text:
                    fragments.append(text)
        return "\n".join(fragments).strip()
    return ""


def _stringify_timestamp(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_sortable_timestamp(value: Any, fallback: int) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return float(fallback)
