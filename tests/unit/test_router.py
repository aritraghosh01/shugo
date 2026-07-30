import pytest

from shugo import router
from shugo.errors import ShugoError


def test_namespace_roundtrip():
    assert router.namespace("github", "get_repo") == "github__get_repo"
    assert router.unpack("github__get_repo") == ("github", "get_repo")


def test_namespace_preserves_tool_underscores():
    q = router.namespace("gh", "get__something")
    server, tool = router.unpack(q)
    assert server == "gh"
    assert tool == "get__something"


def test_server_may_not_contain_separator():
    with pytest.raises(ShugoError):
        router.namespace("bad__server", "tool")


def test_unpack_requires_separator():
    with pytest.raises(ShugoError):
        router.unpack("no_separator")


def test_unpack_rejects_empty_parts():
    with pytest.raises(ShugoError):
        router.unpack("__tool")
    with pytest.raises(ShugoError):
        router.unpack("server__")
