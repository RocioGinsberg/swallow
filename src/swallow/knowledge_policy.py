from __future__ import annotations

from .models import KnowledgePolicyFinding, KnowledgePolicyResult, TaskState


def evaluate_knowledge_policy(state: TaskState) -> KnowledgePolicyResult:
    findings: list[KnowledgePolicyFinding] = []
    knowledge_objects = state.knowledge_objects or []

    if not knowledge_objects:
        findings.append(
            KnowledgePolicyFinding(
                code="knowledge.none_declared",
                level="pass",
                message="No external knowledge objects were declared for this task.",
                details={"count": 0},
            )
        )
    for item in knowledge_objects:
        object_id = str(item.get("object_id", "unknown"))
        stage = str(item.get("stage", "raw"))
        evidence_status = str(item.get("evidence_status", "unbacked"))
        source_ref = str(item.get("source_ref", ""))
        artifact_ref = str(item.get("artifact_ref", ""))

        if stage == "canonical":
            if evidence_status == "artifact_backed":
                findings.append(
                    KnowledgePolicyFinding(
                        code="knowledge.canonical.artifact_backed",
                        level="pass",
                        message="Canonical knowledge object is artifact-backed.",
                        details={"object_id": object_id, "stage": stage, "artifact_ref": artifact_ref},
                    )
                )
            else:
                findings.append(
                    KnowledgePolicyFinding(
                        code="knowledge.canonical.evidence_missing",
                        level="fail",
                        message="Canonical knowledge objects require artifact-backed evidence.",
                        details={"object_id": object_id, "stage": stage, "evidence_status": evidence_status},
                    )
                )
        elif stage == "verified":
            if evidence_status in {"artifact_backed", "source_only"}:
                level = "pass" if evidence_status == "artifact_backed" else "warn"
                findings.append(
                    KnowledgePolicyFinding(
                        code="knowledge.verified.evidence_declared",
                        level=level,
                        message=(
                            "Verified knowledge object carries artifact-backed evidence."
                            if evidence_status == "artifact_backed"
                            else "Verified knowledge object is only source-backed; review before promotion."
                        ),
                        details={"object_id": object_id, "stage": stage, "evidence_status": evidence_status},
                    )
                )
            else:
                findings.append(
                    KnowledgePolicyFinding(
                        code="knowledge.verified.evidence_missing",
                        level="fail",
                        message="Verified knowledge objects require at least source-backed evidence.",
                        details={"object_id": object_id, "stage": stage, "evidence_status": evidence_status},
                    )
                )
        elif stage == "candidate":
            level = "warn" if evidence_status == "unbacked" else "pass"
            findings.append(
                KnowledgePolicyFinding(
                    code="knowledge.candidate.staged",
                    level=level,
                    message=(
                        "Candidate knowledge object is staged with supporting evidence."
                        if evidence_status != "unbacked"
                        else "Candidate knowledge object is unbacked and should be reviewed before promotion."
                    ),
                    details={"object_id": object_id, "stage": stage, "evidence_status": evidence_status},
                )
            )
        else:
            findings.append(
                KnowledgePolicyFinding(
                    code="knowledge.raw.captured",
                    level="pass" if (source_ref or artifact_ref) else "warn",
                    message=(
                        "Raw knowledge object preserves at least one source or artifact reference."
                        if (source_ref or artifact_ref)
                        else "Raw knowledge object was captured without explicit evidence linkage."
                    ),
                    details={"object_id": object_id, "stage": stage, "evidence_status": evidence_status},
                )
            )

    if any(f.level == "fail" for f in findings):
        status = "failed"
    elif any(f.level == "warn" for f in findings):
        status = "warning"
    else:
        status = "passed"

    message_map = {
        "failed": "Knowledge policy found at least one blocking promotion or verification mismatch.",
        "warning": "Knowledge policy passed with warnings.",
        "passed": "Knowledge policy passed.",
    }
    return KnowledgePolicyResult(status=status, message=message_map[status], findings=findings)


def build_knowledge_policy_report(result: KnowledgePolicyResult) -> str:
    lines = [
        "# Knowledge Policy Report",
        "",
        f"- status: {result.status}",
        f"- message: {result.message}",
        "",
        "## Findings",
    ]
    for finding in result.findings:
        lines.append(f"- [{finding.level}] {finding.code}: {finding.message}")
        if finding.details:
            details = ", ".join(f"{key}={value}" for key, value in finding.details.items())
            lines.append(f"  details: {details}")
    return "\n".join(lines)
