import json

import pytest
from aiohttp.test_utils import AioHTTPTestCase, TestClient, TestServer

from shugo.approval.http_ui import build_app


def _seed(home, pid="req-1"):
    (home / "pending").mkdir(parents=True, exist_ok=True)
    (home / "approved").mkdir(parents=True, exist_ok=True)
    (home / "denied").mkdir(parents=True, exist_ok=True)
    (home / "timeout").mkdir(parents=True, exist_ok=True)
    (home / "pending" / f"{pid}.json").write_text(
        json.dumps(
            {
                "id": pid,
                "server": "gh",
                "tool": "create_pr",
                "args": {"title": "hi"},
                "rule_id": "r1",
                "reason": "escalated",
                "controls": ["EU-AI-ACT-ART-14"],
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_index_returns_html(tmp_path, aiohttp_client):
    _seed(tmp_path)
    client = await aiohttp_client(build_app(tmp_path))
    r = await client.get("/")
    assert r.status == 200
    body = await r.text()
    assert "SHUGO" in body
    assert "/api/pending" in body


@pytest.mark.asyncio
async def test_api_pending_returns_seeded_entries(tmp_path, aiohttp_client):
    _seed(tmp_path, "a")
    _seed(tmp_path, "b")
    client = await aiohttp_client(build_app(tmp_path))
    r = await client.get("/api/pending")
    assert r.status == 200
    data = await r.json()
    assert sorted(e["id"] for e in data) == ["a", "b"]


@pytest.mark.asyncio
async def test_api_verdict_approve_moves_file(tmp_path, aiohttp_client):
    _seed(tmp_path, "req-x")
    client = await aiohttp_client(build_app(tmp_path))
    r = await client.post("/api/verdict/req-x", json={"decision": "allow"})
    assert r.status == 200
    assert (tmp_path / "approved" / "req-x.json").exists()
    assert not (tmp_path / "pending" / "req-x.json").exists()


@pytest.mark.asyncio
async def test_api_verdict_deny_records_note(tmp_path, aiohttp_client):
    _seed(tmp_path, "req-y")
    client = await aiohttp_client(build_app(tmp_path))
    r = await client.post("/api/verdict/req-y", json={"decision": "deny", "note": "not safe"})
    assert r.status == 200
    data = json.loads((tmp_path / "denied" / "req-y.json").read_text())
    assert data["_note"] == "not safe"
    assert data["_approver"] == "http-ui"


@pytest.mark.asyncio
async def test_api_verdict_missing_pending_returns_404(tmp_path, aiohttp_client):
    (tmp_path / "pending").mkdir()
    (tmp_path / "approved").mkdir()
    client = await aiohttp_client(build_app(tmp_path))
    r = await client.post("/api/verdict/does-not-exist", json={"decision": "allow"})
    assert r.status == 404


@pytest.mark.asyncio
async def test_api_verdict_bad_decision_returns_400(tmp_path, aiohttp_client):
    _seed(tmp_path)
    client = await aiohttp_client(build_app(tmp_path))
    r = await client.post("/api/verdict/req-1", json={"decision": "maybe"})
    assert r.status == 400
