from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .parsers import ConversationTurn


KEEP_KEYWORDS: tuple[str, ...] = (
    "决定",
    "约束",
    "方案",
    "结论",
    "不做",
    "取舍",
    "风险",
    "边界",
    "decision",
    "constraint",
    "constraints",
    "proposal",
    "plan",
    "non-goal",
    "non-goals",
    "tradeoff",
    "trade-off",
    "risk",
    "risks",
    "outcome",
)
CHATTER_EXACT_MATCHES: tuple[str, ...] = (
    "ok",
    "okay",
    "好的",
    "好",
    "收到",
    "明白了",
    "明白",
    "谢谢",
    "感谢",
    "thanks",
    "thank you",
    "got it",
    "sounds good",
)
CHATTER_PREFIXES: tuple[str, ...] = (
    "好的",
    "谢谢",
    "感谢",
    "ok",
    "okay",
    "got it",
    "明白",
)


@dataclass(slots=True)
class ExtractedFragment:
    role: str
    text: str
    source_turn_ids: list[str] = field(default_factory=list)
    source_timestamps: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.role = self.role.strip().lower()
        self.text = self.text.strip()
        self.source_turn_ids = [item.strip() for item in self.source_turn_ids if item.strip()]
        self.source_timestamps = [item.strip() for item in self.source_timestamps if item.strip()]
        self.signals = [item.strip() for item in self.signals if item.strip()]
        self.metadata = {str(key).strip(): str(value).strip() for key, value in self.metadata.items() if str(key).strip()}
        if not self.role:
            raise ValueError("fragment role must be a non-empty string")
        if not self.text:
            raise ValueError("fragment text must be a non-empty string")


def merge_conversation_turns(turns: list[ConversationTurn]) -> list[ConversationTurn]:
    if not turns:
        return []

    merged: list[ConversationTurn] = []
    for turn in turns:
        if not merged or merged[-1].role != turn.role:
            merged.append(
                ConversationTurn(
                    role=turn.role,
                    content=turn.content,
                    timestamp=turn.timestamp,
                    turn_id=turn.turn_id,
                    metadata=dict(turn.metadata),
                )
            )
            continue

        previous = merged[-1]
        combined_ids = _merge_metadata_values(previous.metadata.get("merged_turn_ids", previous.turn_id), turn.turn_id)
        combined_timestamps = _merge_metadata_values(
            previous.metadata.get("merged_timestamps", previous.timestamp),
            turn.timestamp,
        )
        combined_metadata = dict(previous.metadata)
        combined_metadata["merged_turn_ids"] = combined_ids
        if combined_timestamps:
            combined_metadata["merged_timestamps"] = combined_timestamps
        for key, value in turn.metadata.items():
            if key not in combined_metadata and value:
                combined_metadata[key] = value
        merged[-1] = ConversationTurn(
            role=previous.role,
            content=f"{previous.content}\n\n{turn.content}".strip(),
            timestamp=previous.timestamp or turn.timestamp,
            turn_id=previous.turn_id or turn.turn_id,
            metadata=combined_metadata,
        )
    return merged


def filter_conversation_turns(turns: list[ConversationTurn]) -> list[ExtractedFragment]:
    if not turns:
        return []

    fragments: list[ExtractedFragment] = []
    seen: set[str] = set()
    for turn in merge_conversation_turns(turns):
        signals = _classify_signals(turn.content, turn.role)
        if "drop_chatter" in signals:
            continue
        dedupe_key = _normalize_fragment_text(turn.content)
        if not dedupe_key or dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        fragments.append(
            ExtractedFragment(
                role=turn.role,
                text=turn.content.strip(),
                source_turn_ids=_split_metadata_values(turn.metadata.get("merged_turn_ids", turn.turn_id)),
                source_timestamps=_split_metadata_values(turn.metadata.get("merged_timestamps", turn.timestamp)),
                signals=[signal for signal in signals if signal != "drop_chatter"],
                metadata=dict(turn.metadata),
            )
        )
    return fragments


def _classify_signals(text: str, role: str) -> list[str]:
    signals: list[str] = []
    normalized = text.strip()
    lowered = normalized.lower()
    if _is_chatter(lowered):
        signals.append("drop_chatter")
        return signals
    if "```" in normalized:
        signals.append("code_block")
    if re.search(r"(^|\n)\s*([-*]|\d+\.)\s+\S", normalized):
        signals.append("list")
    if any(keyword in lowered for keyword in KEEP_KEYWORDS):
        signals.append("keyword")
    if role == "document":
        signals.append("document")
    if not signals:
        signals.append("context")
    return signals


def _is_chatter(lowered: str) -> bool:
    compact = " ".join(lowered.split())
    if compact in CHATTER_EXACT_MATCHES:
        return True
    if len(compact) <= 24 and any(compact.startswith(prefix) for prefix in CHATTER_PREFIXES):
        return True
    return False


def _normalize_fragment_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.lower()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[^\w\u4e00-\u9fff`#:+./-]+", " ", normalized)
    return " ".join(normalized.split())


def _merge_metadata_values(left: str, right: str) -> str:
    values: list[str] = []
    seen: set[str] = set()
    for raw in (left, right):
        for item in _split_metadata_values(raw):
            if item not in seen:
                seen.add(item)
                values.append(item)
    return ",".join(values)


def _split_metadata_values(raw: str) -> list[str]:
    values = [item.strip() for item in str(raw).split(",")]
    return [item for item in values if item]
