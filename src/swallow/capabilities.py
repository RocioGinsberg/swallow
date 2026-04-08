from __future__ import annotations

from .models import CapabilityAssembly, CapabilityManifest


DEFAULT_CAPABILITY_MANIFEST = CapabilityManifest(
    profile_refs=["baseline_local"],
    workflow_refs=["task_loop"],
    validator_refs=["run_output_validation"],
)

KNOWN_PROFILE_REFS = {"baseline_local", "research_local"}
KNOWN_WORKFLOW_REFS = {"task_loop"}
KNOWN_VALIDATOR_REFS = {"run_output_validation", "strict_validation"}
KNOWN_SKILL_REFS = {"plan-task"}
KNOWN_TOOL_REFS = {"doctor.codex"}


def parse_capability_refs(raw_values: list[str] | None) -> CapabilityManifest:
    if not raw_values:
        return DEFAULT_CAPABILITY_MANIFEST

    manifest = CapabilityManifest()
    for raw_value in raw_values:
        if not raw_value:
            continue
        kind, _, ref = raw_value.partition(":")
        ref = ref.strip()
        kind = kind.strip()
        if not ref or not kind:
            continue
        if kind == "profile":
            manifest.profile_refs.append(ref)
        elif kind == "workflow":
            manifest.workflow_refs.append(ref)
        elif kind == "validator":
            manifest.validator_refs.append(ref)
        elif kind == "skill":
            manifest.skill_refs.append(ref)
        elif kind == "tool":
            manifest.tool_refs.append(ref)

    if not manifest.has_entries():
        return DEFAULT_CAPABILITY_MANIFEST
    return manifest


def build_capability_assembly(manifest: CapabilityManifest) -> CapabilityAssembly:
    notes = ["Assembled from the local baseline capability set."]
    return CapabilityAssembly(
        requested=manifest.to_dict(),
        effective=manifest.to_dict(),
        assembly_status="assembled",
        resolver="local_baseline",
        notes=notes,
    )


def validate_capability_manifest(manifest: CapabilityManifest) -> list[str]:
    errors: list[str] = []

    for ref in manifest.profile_refs:
        if ref not in KNOWN_PROFILE_REFS:
            errors.append(f"Unknown profile capability: {ref}")
    for ref in manifest.workflow_refs:
        if ref not in KNOWN_WORKFLOW_REFS:
            errors.append(f"Unknown workflow capability: {ref}")
    for ref in manifest.validator_refs:
        if ref not in KNOWN_VALIDATOR_REFS:
            errors.append(f"Unknown validator capability: {ref}")
    for ref in manifest.skill_refs:
        if ref not in KNOWN_SKILL_REFS:
            errors.append(f"Unknown skill capability: {ref}")
    for ref in manifest.tool_refs:
        if ref not in KNOWN_TOOL_REFS:
            errors.append(f"Unknown tool capability: {ref}")

    return errors
