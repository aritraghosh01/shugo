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
