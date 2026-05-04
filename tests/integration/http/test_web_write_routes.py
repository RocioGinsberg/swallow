from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from swallow.application.commands.meta_optimizer import run_meta_optimizer_command
from swallow.knowledge_retrieval.knowledge_plane import (
    StagedCandidate,
    list_staged_knowledge as load_staged_candidates,
    submit_staged_knowledge as submit_staged_candidate,
)
from swallow.provider_router.router import load_route_weights, route_by_name
from swallow.application.infrastructure.paths import canonical_registry_path, latest_optimization_proposal_bundle_path, route_weights_path
from swallow.adapters.http.api import create_fastapi_app
from swallow.truth_governance.store import load_state


def _client(base_dir: Path) -> TestClient:
    return TestClient(create_fastapi_app(base_dir))


def _write_events(task_dir: Path, records: list[dict[str, object]]) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "events.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def _relative(base_dir: Path, path: Path) -> str:
    return path.relative_to(base_dir).as_posix()


def test_task_lifecycle_write_routes_create_run_and_report_conflicts(tmp_path: Path) -> None:
    client = _client(tmp_path)

    create_response = client.post(
        "/api/tasks",
        json={
            "title": "HTTP task",
            "goal": "Exercise local FastAPI write routes.",
            "executor_name": "local",
        },
    )

    assert create_response.status_code == 200
    assert create_response.json()["ok"] is True
    created = create_response.json()["data"]["task"]
    task_id = created["task_id"]
    assert created["status"] == "created"
    persisted = load_state(tmp_path, task_id)
    assert persisted.title == "HTTP task"
    assert persisted.goal == "Exercise local FastAPI write routes."

    run_response = client.post(f"/api/tasks/{task_id}/run", json={})

    assert run_response.status_code == 200
    assert run_response.json()["data"]["task"]["status"] == "completed"

    missing_response = client.post("/api/tasks/missing-task/run", json={})

    assert missing_response.status_code == 404

    retry_response = client.post(f"/api/tasks/{task_id}/retry", json={})

    assert retry_response.status_code == 409
    assert "retry" in str(retry_response.json()["detail"])


def test_task_create_rejects_client_workspace_root(tmp_path: Path) -> None:
    response = _client(tmp_path).post(
        "/api/tasks",
        json={
            "title": "Bad HTTP task",
            "goal": "Attempt to supply a workspace root.",
            "workspace_root": "/tmp/not-allowed",
        },
    )

    assert response.status_code == 422
    assert "workspace_root" in str(response.json()["detail"])


def test_task_create_rejects_field_type_errors_with_validation_status(tmp_path: Path) -> None:
    response = _client(tmp_path).post(
        "/api/tasks",
        json={
            "title": 123,
            "goal": "Invalid title type.",
        },
    )

    assert response.status_code == 422
    assert "title" in str(response.json()["detail"])


def test_task_resume_reports_blocked_state_as_conflict(tmp_path: Path) -> None:
    client = _client(tmp_path)
    created = client.post(
        "/api/tasks",
        json={
            "title": "Blocked resume task",
            "goal": "Resume should be blocked before a checkpoint exists.",
        },
    ).json()["data"]["task"]

    response = client.post(f"/api/tasks/{created['task_id']}/resume", json={})

    assert response.status_code == 409
    assert "resume" in str(response.json()["detail"])


def test_knowledge_stage_promote_and_reject_routes(tmp_path: Path) -> None:
    promote_candidate = submit_staged_candidate(
        tmp_path,
        StagedCandidate(
            candidate_id="",
            text="Promote through HTTP.",
            source_task_id="http-task",
            source_object_id="knowledge-1",
            submitted_by="integration-test",
        ),
    )
    reject_candidate = submit_staged_candidate(
        tmp_path,
        StagedCandidate(
            candidate_id="",
            text="Reject through HTTP.",
            source_task_id="http-task",
            source_object_id="knowledge-2",
            submitted_by="integration-test",
        ),
    )
    client = _client(tmp_path)

    promote_response = client.post(
        f"/api/knowledge/staged/{promote_candidate.candidate_id}/promote",
        json={"note": "Approved from HTTP."},
    )
    reject_response = client.post(
        f"/api/knowledge/staged/{reject_candidate.candidate_id}/reject",
        json={"note": "Rejected from HTTP."},
    )

    assert promote_response.status_code == 200
    assert reject_response.status_code == 200
    assert promote_response.json()["ok"] is True
    assert promote_response.json()["data"]["candidate"]["status"] == "promoted"
    assert reject_response.json()["data"]["candidate"]["status"] == "rejected"
    staged = {candidate.candidate_id: candidate for candidate in load_staged_candidates(tmp_path)}
    assert staged[promote_candidate.candidate_id].status == "promoted"
    assert staged[reject_candidate.candidate_id].status == "rejected"
    canonical_records = [
        json.loads(line)
        for line in canonical_registry_path(tmp_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert canonical_records[0]["canonical_id"] == f"canonical-{promote_candidate.candidate_id}"


def test_knowledge_stage_routes_return_not_found_for_unknown_candidate(tmp_path: Path) -> None:
    response = _client(tmp_path).post(
        "/api/knowledge/staged/staged-missing/promote",
        json={"note": "No candidate exists."},
    )

    assert response.status_code == 404
    assert "Unknown staged candidate" in response.json()["detail"]


def test_knowledge_stage_promote_does_not_expose_force_bypass(tmp_path: Path) -> None:
    candidate = submit_staged_candidate(
        tmp_path,
        StagedCandidate(
            candidate_id="",
            text="Force should not be accepted through HTTP.",
            source_task_id="http-task",
            source_object_id="knowledge-force",
            submitted_by="integration-test",
        ),
    )

    response = _client(tmp_path).post(
        f"/api/knowledge/staged/{candidate.candidate_id}/promote",
        json={"note": "No force in web schema.", "force": True},
    )

    assert response.status_code == 422
    assert "force" in str(response.json()["detail"])


def test_proposal_review_apply_routes_use_workspace_relative_paths(tmp_path: Path) -> None:
    route = route_by_name("local-codex")
    assert route is not None
    original_weight = route.quality_weight
    try:
        _write_events(
            tmp_path / ".swl" / "tasks" / "http-proposal-task",
            [
                {
                    "task_id": "http-proposal-task",
                    "event_type": "executor.failed",
                    "message": "Local codex failed.",
                    "payload": {
                        "physical_route": "local-codex",
                        "logical_model": "codex",
                        "task_family": "execution",
                        "latency_ms": 12,
                        "token_cost": 0.0,
                        "degraded": False,
                        "failure_kind": "launch_error",
                        "error_code": "launch_error",
                    },
                },
                {
                    "task_id": "http-proposal-task",
                    "event_type": "executor.failed",
                    "message": "Local codex failed again.",
                    "payload": {
                        "physical_route": "local-codex",
                        "logical_model": "codex",
                        "task_family": "execution",
                        "latency_ms": 9,
                        "token_cost": 0.0,
                        "degraded": False,
                        "failure_kind": "launch_error",
                        "error_code": "launch_error",
                    },
                },
            ],
        )
        run_meta_optimizer_command(tmp_path, last_n=100)
        bundle_path = latest_optimization_proposal_bundle_path(tmp_path)

        client = _client(tmp_path)
        absolute_response = client.post("/api/proposals/review", json={"bundle_path": str(bundle_path), "decision": "approved"})
        traversal_response = client.post("/api/proposals/review", json={"bundle_path": "../outside.json", "decision": "approved"})
        missing_response = client.post("/api/proposals/review", json={"bundle_path": ".swl/meta_optimizer/missing.json", "decision": "approved"})
        review_response = client.post(
            "/api/proposals/review",
            json={
                "bundle_path": _relative(tmp_path, bundle_path),
                "decision": "approved",
                "note": "Reviewed from HTTP.",
            },
        )

        assert absolute_response.status_code == 400
        assert traversal_response.status_code == 400
        assert missing_response.status_code == 404
        assert review_response.status_code == 200
        review_payload = review_response.json()["data"]
        assert review_payload["review_record"]["decision"] == "approved"
        review_path = review_payload["record_path"]

        apply_response = client.post("/api/proposals/apply", json={"review_path": review_path})

        assert apply_response.status_code == 200
        assert apply_response.json()["data"]["application_record"]["applied_count"] >= 1
        assert "local-codex" in load_route_weights(tmp_path)
        assert not route_weights_path(tmp_path).exists()
    finally:
        route.quality_weight = original_weight


def test_write_routes_publish_response_models_in_openapi(tmp_path: Path) -> None:
    openapi = _client(tmp_path).get("/openapi.json").json()

    task_create_schema = openapi["paths"]["/api/tasks"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
    promote_schema = openapi["paths"]["/api/knowledge/staged/{candidate_id}/promote"]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]

    assert task_create_schema["$ref"].endswith("/TaskEnvelope")
    assert promote_schema["$ref"].endswith("/StagePromoteEnvelope")
