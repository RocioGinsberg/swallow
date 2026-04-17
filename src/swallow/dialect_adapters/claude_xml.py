from __future__ import annotations

from xml.sax.saxutils import escape

from ..models import DialectSpec, RetrievalItem, TaskState


def _items_block(tag_name: str, items: list[str]) -> list[str]:
    if not items:
        return [f"  <{tag_name}>none</{tag_name}>"]
    lines = [f"  <{tag_name}>"]
    for item in items:
        lines.append(f"    <item>{escape(item)}</item>")
    lines.append(f"  </{tag_name}>")
    return lines


class ClaudeXMLDialect:
    spec = DialectSpec(
        name="claude_xml",
        description="XML-tagged prompt layout for Claude-family models.",
        supported_model_hints=["claude"],
    )

    def format_prompt(self, raw_prompt: str, state: TaskState, retrieval_items: list[RetrievalItem]) -> str:
        semantics = state.task_semantics or {}
        constraints = [str(item).strip() for item in semantics.get("constraints", []) if str(item).strip()]
        acceptance = [str(item).strip() for item in semantics.get("acceptance_criteria", []) if str(item).strip()]
        retrieval_lines = [
            f"[{item.source_type}] {item.reference()} title={item.display_title()}: {item.preview}"
            for item in retrieval_items
        ]
        instructions = [
            "Return what you would do next.",
            "Call out the main risks or gaps.",
            "End with the first concrete implementation action.",
        ]
        lines = [
            "<swallow_task>",
            "  <task>",
            f"    <id>{escape(state.task_id)}</id>",
            f"    <title>{escape(state.title)}</title>",
            f"    <goal>{escape(state.goal)}</goal>",
            "  </task>",
            "  <context>",
            f"    <route_name>{escape(state.route_name)}</route_name>",
            f"    <route_backend>{escape(state.route_backend)}</route_backend>",
            f"    <model_hint>{escape(state.route_model_hint)}</model_hint>",
            f"    <dialect>{escape(state.route_dialect or self.spec.name)}</dialect>",
            "  </context>",
        ]
        lines.extend(_items_block("constraints", constraints))
        lines.extend(_items_block("acceptance_criteria", acceptance))
        lines.extend(_items_block("retrieval", retrieval_lines))
        lines.extend(_items_block("instructions", instructions))
        lines.extend(
            [
                "  <raw_prompt>",
                escape(raw_prompt),
                "  </raw_prompt>",
                "</swallow_task>",
            ]
        )
        return "\n".join(lines)
