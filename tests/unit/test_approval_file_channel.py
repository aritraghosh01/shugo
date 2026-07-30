import asyncio
import json

import pytest

from shugo.approval.channel import PendingApproval
from shugo.approval.file_channel import FileApprovalChannel, apply_verdict, list_pending


def _pending(id_="req-1", timeout_s=2):
    return PendingApproval(
        id=id_,
        ts="2026-07-30T00:00:00+00:00",
        server="gh",
        tool="create_pr",
        args={"title": "hi"},
        rule_id="r1",
        reason="write escalated",
        timeout_s=timeout_s,
        pid=12345,
        controls=("EU-AI-ACT-ART-14",),
    )


@pytest.mark.asyncio
async def test_request_returns_allow_when_approved(tmp_path):
    ch = FileApprovalChannel(home=tmp_path)
    pending = _pending(timeout_s=5)

    async def approve_soon():
        await asyncio.sleep(0.4)
        apply_verdict(tmp_path, "req-1", "allow", approver="tester")

    verdict, _ = await asyncio.gather(ch.request(pending), approve_soon())
    assert verdict.kind == "allow"
    assert verdict.approver == "tester"


@pytest.mark.asyncio
async def test_request_returns_deny_when_denied(tmp_path):
    ch = FileApprovalChannel(home=tmp_path)
    pending = _pending(timeout_s=5)

    async def deny_soon():
        await asyncio.sleep(0.4)
        apply_verdict(tmp_path, "req-1", "deny", approver="tester", note="nope")

    verdict, _ = await asyncio.gather(ch.request(pending), deny_soon())
    assert verdict.kind == "deny"
    assert verdict.note == "nope"


@pytest.mark.asyncio
async def test_request_times_out(tmp_path):
    ch = FileApprovalChannel(home=tmp_path)
    pending = _pending(timeout_s=1)
    verdict = await ch.request(pending)
    assert verdict.kind == "timeout"
    assert (tmp_path / "timeout" / "req-1.json").exists()


def test_pending_file_written_atomically(tmp_path):
    ch = FileApprovalChannel(home=tmp_path)

    async def check_pending_exists():
        # kick off request in background
        loop = asyncio.get_event_loop()
        task = loop.create_task(ch.request(_pending(timeout_s=1)))
        await asyncio.sleep(0.2)
        assert (tmp_path / "pending" / "req-1.json").exists()
        data = json.loads((tmp_path / "pending" / "req-1.json").read_text())
        assert data["server"] == "gh"
        assert data["tool"] == "create_pr"
        # let it time out
        await task

    asyncio.run(check_pending_exists())


def test_apply_verdict_missing_pending_raises(tmp_path):
    (tmp_path / "pending").mkdir()
    (tmp_path / "approved").mkdir()
    with pytest.raises(FileNotFoundError):
        apply_verdict(tmp_path, "does-not-exist", "allow")


def test_list_pending_returns_entries(tmp_path):
    (tmp_path / "pending").mkdir()
    (tmp_path / "pending" / "a.json").write_text(
        json.dumps({"id": "a", "server": "gh", "tool": "t"}), encoding="utf-8"
    )
    (tmp_path / "pending" / "b.json").write_text(
        json.dumps({"id": "b", "server": "gh", "tool": "t2"}), encoding="utf-8"
    )
    (tmp_path / "pending" / ".hidden.tmp").write_text("skip me", encoding="utf-8")
    entries = list_pending(tmp_path)
    assert [e["id"] for e in entries] == ["a", "b"]
