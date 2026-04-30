from __future__ import annotations

from xml.sax.saxutils import escape

from swallow.knowledge_retrieval.dialect_data import collect_prompt_data
from swallow.orchestration.models import DialectSpec, RetrievalItem, TaskState


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
        prompt_data = collect_prompt_data(state, retrieval_items)
        constraints = prompt_data.semantics.constraints if prompt_data.semantics is not None else []
        acceptance = prompt_data.semantics.acceptance_criteria if prompt_data.semantics is not None else []
        retrieval_lines = prompt_data.retrieval_entries
        instructions = [
            "Return what you would do next.",
            "Call out the main risks or gaps.",
            "End with the first concrete implementation action.",
        ]
        lines = [
            "<swallow_task>",
            "  <task>",
            f"    <id>{escape(prompt_data.task.task_id)}</id>",
            f"    <title>{escape(prompt_data.task.title)}</title>",
            f"    <goal>{escape(prompt_data.task.goal)}</goal>",
            "  </task>",
            "  <context>",
            f"    <route_name>{escape(prompt_data.route.route_name)}</route_name>",
            f"    <route_backend>{escape(prompt_data.route.route_backend)}</route_backend>",
            f"    <model_hint>{escape(prompt_data.route.route_model_hint)}</model_hint>",
            f"    <dialect>{escape(prompt_data.route.route_dialect or self.spec.name)}</dialect>",
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
