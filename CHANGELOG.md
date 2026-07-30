# Changelog

All notable changes to SHUGO will be documented here. This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project skeleton and packaging (`pyproject.toml`, `src/shugo/` layout).
- Typer-based CLI surface with all v0.1 subcommand stubs: `serve`, `init`, `validate`, `explain`, `audit tail|verify`, `evidence`, `approve`, `deny`, `halt`, `unhalt`.
- Cross-platform `~/.shugo/` layout helpers (`SHUGO_HOME` override supported).
- GitHub Actions CI matrix (Python 3.11–3.13 × macOS / Ubuntu / Windows).
- Policy models (`shugo.policy.models`): Pydantic v2, `extra=forbid`, unique rule ids, `escalate` requires an `approval` block.
- Policy loader (`shugo.policy.loader.load_config`): YAML parse + schema validate with clear error messages.
- Policy engine (`shugo.policy.engine.PolicyEngine`): deny-by-default, first-match-wins, `fnmatch` globs on server/tool, nested-equality on args.
- Working `shugo validate` and `shugo explain` commands.
- `policies/starter.yaml` reference policy modeled on the README example.
- Audit log (`shugo.audit`): append-only JSONL with rolling SHA-256 hash chain (seed = 64×"0"), NFC-normalized canonical JSON, per-line `os.fsync`, thread-safe append. Redaction of dotted arg paths is applied before hashing so log and hash agree.
- Log verification (`shugo audit verify`): streams each line, recomputes hash, checks both `this_hash` and next `prev_hash`. Reports first divergence with line number and exits non-zero.
- `shugo audit tail [-n N] [-f]` and `shugo halt` / `shugo unhalt` kill-switch controls (writes `~/.shugo/HALT`).
- Router (`shugo.router`): namespaces tools as `<server>__<tool>` so multiple upstreams merge cleanly under a single `tools/list`.
- Upstream (`shugo.upstream.StdioUpstream`): MCP client wrapping a stdio subprocess per upstream, managed via `AsyncExitStack` for clean teardown.
- Proxy (`shugo.proxy`): full async MCP server that intercepts `tools/list` and `tools/call`, routes to the right upstream, evaluates policy, records to the audit log, and respects the HALT sentinel. `serve_with_upstreams(...)` is exposed for integration tests using in-memory streams and fake upstreams.
- Working `shugo serve` with allow/deny paths (escalate temporarily rendered as deny; PR #5 wires real approvals).
- File-drop approval channel (`shugo.approval.FileApprovalChannel`): proxy writes `~/.shugo/pending/<uuid>.json`, blocks on 250 ms poll of the `approved/` / `denied/` / `timeout/` directories; verdicts move atomically via `os.replace`.
- Sidecar TUI (`shugo approve --watch`): polls the pending queue and prompts approve/deny/skip per request.
- One-shot CLI: `shugo approve <id>` and `shugo deny <id> [--note NOTE]`.
- Proxy escalate path now fully wired: request-approval, on-timeout honors policy (`allow` or `deny`), audit log records approver.
- Opt-in local HTTP approval UI (`shugo.approval.http_ui`): single-file HTML page + `GET /api/pending` + `POST /api/verdict/<id>`. Bound to `127.0.0.1` only; shares the file-drop backend so `shugo approve --watch` and the browser resolve the same queue.
- `shugo serve --approvals file|http|both --approvals-port N` (default port 6247).
