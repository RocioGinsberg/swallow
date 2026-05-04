from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from swallow.adapters.http.api import create_fastapi_app
from swallow.application.commands.knowledge import StagedCandidate
from swallow.application.commands.wiki import WikiCompilerRunResult
from swallow.application.infrastructure.paths import artifacts_dir
from swallow.application.services.wiki_jobs import create_wiki_draft_job, run_wiki_job
from swallow.knowledge_retrieval.knowledge_plane import load_task_knowledge_view, persist_task_knowledge_view
from swallow.orchestration.orchestrator import create_task


def _client(base_dir: Path) -> TestClient:
    return TestClient(create_fastapi_app(base_dir))


def test_wiki_draft_route_creates_queued_artifact_job_without_inline_execution(tmp_path: Path) -> None:
    state = create_task(
        base_dir=tmp_path,
        title="HTTP wiki draft",
        goal="Queue a Wiki Compiler draft from HTTP.",
        workspace_root=tmp_path,
    )
    client = _client(tmp_path)

    with patch("swallow.adapters.http.api.run_wiki_job", return_value=None) as runner:
        response = client.post(
            "/api/wiki/draft",
            json={
                "task_id": state.task_id,
                "topic": "compiler",
                "source_refs": ["file://workspace/compiler.md"],
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    job = payload["data"]["job"]
    assert job["job_id"].startswith("wiki-job-")
    assert job["task_id"] == state.task_id
    assert job["action"] == "draft"
    assert job["status"] == "queued"
    assert job["topic"] == "compiler"
    runner.assert_called_once_with(tmp_path, job["job_id"])

    job_path = artifacts_dir(tmp_path, state.task_id) / "wiki_jobs" / f"{job['job_id']}.json"
    persisted = json.loads(job_path.read_text(encoding="utf-8"))
    assert persisted["status"] == "queued"
    assert persisted["source_refs"] == ["file://workspace/compiler.md"]


def test_wiki_refine_route_creates_queued_artifact_job(tmp_path: Path) -> None:
    state = create_task(
        base_dir=tmp_path,
        title="HTTP wiki refine",
        goal="Queue a Wiki Compiler refinement from HTTP.",
        workspace_root=tmp_path,
    )

    with patch("swallow.adapters.http.api.run_wiki_job", return_value=None):
        response = _client(tmp_path).post(
            "/api/wiki/refine",
            json={
                "task_id": state.task_id,
                "mode": "supersede",
                "target_object_id": "wiki-old",
                "source_refs": ["file://workspace/refine.md"],
            },
        )

    assert response.status_code == 200
    job = response.json()["data"]["job"]
    assert job["action"] == "refine"
    assert job["status"] == "queued"
    assert job["mode"] == "supersede"
    assert job["target_object_id"] == "wiki-old"


def test_wiki_job_status_and_result_routes_return_completed_payload(tmp_path: Path) -> None:
    state = create_task(
        base_dir=tmp_path,
        title="HTTP wiki job result",
        goal="Read a completed Wiki Compiler job result.",
        workspace_root=tmp_path,
    )
    job = create_wiki_draft_job(
        tmp_path,
        task_id=state.task_id,
        topic="compiler",
        source_refs=["file://workspace/compiler.md"],
    )
    fake_candidate = StagedCandidate(
        candidate_id="staged-web-job",
        text="A staged wiki candidate from a completed job.",
        source_task_id=state.task_id,
        submitted_by="wiki-compiler",
        wiki_mode="draft",
    )
    fake_result = WikiCompilerRunResult(
        candidate=fake_candidate,
        prompt_pack={"kind": "wiki_compiler_prompt_pack_v1"},
        compiler_result={"status": "completed", "draft": {"text": fake_candidate.text}},
        source_pack=[{"source_ref": "file://workspace/compiler.md", "parser_version": "wiki-compiler-v1"}],
        prompt_artifact=artifacts_dir(tmp_path, state.task_id) / "wiki_compiler_prompt_pack.json",
        result_artifact=artifacts_dir(tmp_path, state.task_id) / "wiki_compiler_result.json",
    )

    with patch("swallow.application.services.wiki_jobs.draft_wiki_command", return_value=fake_result):
        completed = run_wiki_job(tmp_path, job.job_id)

    assert completed.status == "completed"
    client = _client(tmp_path)
    status_response = client.get(f"/api/wiki/jobs/{job.job_id}")
    result_response = client.get(f"/api/wiki/jobs/{job.job_id}/result")

    assert status_response.status_code == 200
    assert status_response.json()["data"]["job"]["candidate_id"] == "staged-web-job"
    assert status_response.json()["data"]["job"]["status"] == "completed"
    assert result_response.status_code == 200
    result_payload = result_response.json()["data"]
    assert result_payload["result_ready"] is True
    assert result_payload["candidate"]["candidate_id"] == "staged-web-job"
    assert result_payload["compiler_result"]["status"] == "completed"
    assert result_payload["source_pack"][0]["parser_version"] == "wiki-compiler-v1"


def test_wiki_refresh_evidence_route_updates_anchor_without_llm(tmp_path: Path) -> None:
    state = create_task(
        base_dir=tmp_path,
        title="HTTP evidence refresh",
        goal="Refresh evidence anchors through HTTP.",
        workspace_root=tmp_path,
    )
    source = tmp_path / "evidence.md"
    source.write_text("# Evidence\n\nFresh HTTP anchor.\n", encoding="utf-8")
    persist_task_knowledge_view(
        tmp_path,
        state.task_id,
        [
            {
                "object_id": "evidence-http",
                "text": "Old evidence.",
                "stage": "raw",
                "source_ref": "",
                "evidence_status": "unbacked",
            }
        ],
    )

    with patch("swallow.application.services.wiki_compiler.call_agent_llm", side_effect=AssertionError("no LLM")):
        response = _client(tmp_path).post(
            "/api/wiki/refresh-evidence",
            json={
                "task_id": state.task_id,
                "target_object_id": "evidence-http",
                "source_ref": "file://workspace/evidence.md",
                "parser_version": "parser-v2",
                "span": "L1-L3",
            },
        )

    assert response.status_code == 200
    refresh = response.json()["data"]["refresh"]
    assert refresh["target_object_id"] == "evidence-http"
    assert refresh["parser_version"] == "parser-v2"
    assert str(refresh["content_hash"]).startswith("sha256:")
    view = [item for item in load_task_knowledge_view(tmp_path, state.task_id) if item["object_id"] == "evidence-http"]
    assert view[0]["span"] == "L1-L3"
    assert view[0]["parser_version"] == "parser-v2"


def test_wiki_routes_publish_response_models_in_openapi(tmp_path: Path) -> None:
    openapi = _client(tmp_path).get("/openapi.json").json()

    draft_schema = openapi["paths"]["/api/wiki/draft"]["post"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    status_schema = openapi["paths"]["/api/wiki/jobs/{job_id}"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    result_schema = openapi["paths"]["/api/wiki/jobs/{job_id}/result"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]

    assert draft_schema["$ref"].endswith("/WikiJobEnvelope")
    assert status_schema["$ref"].endswith("/WikiJobEnvelope")
    assert result_schema["$ref"].endswith("/WikiJobResultEnvelope")
