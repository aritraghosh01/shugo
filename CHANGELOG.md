# Changelog

All notable changes to SHUGO will be documented here. This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project skeleton and packaging (`pyproject.toml`, `src/shugo/` layout).
- Typer-based CLI surface with all v0.1 subcommand stubs: `serve`, `init`, `validate`, `explain`, `audit tail|verify`, `evidence`, `approve`, `deny`, `halt`, `unhalt`.
- Cross-platform `~/.shugo/` layout helpers (`SHUGO_HOME` override supported).
- GitHub Actions CI matrix (Python 3.11–3.13 × macOS / Ubuntu / Windows).
