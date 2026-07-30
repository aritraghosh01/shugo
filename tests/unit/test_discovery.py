import json

from shugo import discovery


def _write_config(path, mcpServers):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"mcpServers": mcpServers}), encoding="utf-8")


def test_parse_client_config_normalizes_names(tmp_path):
    p = tmp_path / "cfg.json"
    _write_config(
        p,
        {
            "MyServer": {"command": "npx", "args": ["-y", "srv"]},
            "with__seps": {"command": "x"},
        },
    )
    servers = discovery.parse_client_config(p)
    names = sorted(s.name for s in servers)
    assert names == ["myserver", "with-seps"]


def test_parse_client_config_skips_bad_entries(tmp_path):
    p = tmp_path / "cfg.json"
    _write_config(
        p,
        {
            "ok": {"command": "npx", "args": ["srv"]},
            "no-cmd": {"args": ["a"]},
            "bad": "not-a-dict",
        },
    )
    servers = discovery.parse_client_config(p)
    assert [s.name for s in servers] == ["ok"]


def test_parse_client_config_accepts_servers_key(tmp_path):
    p = tmp_path / "cfg.json"
    p.write_text(
        json.dumps({"servers": {"one": {"command": "x", "args": ["y"], "env": {"K": "V"}}}}),
        encoding="utf-8",
    )
    servers = discovery.parse_client_config(p)
    assert servers[0].env == {"K": "V"}


def test_default_client_config_paths_platform_specific():
    paths = discovery.default_client_config_paths()
    assert len(paths) >= 2
    # every candidate should be an absolute path
    for p in paths:
        assert p.is_absolute()
