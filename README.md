<div align="center">

<img src="assets/shugo-banner.png" alt="SHUGO — /shoo-go/ · noun · Japanese · guardian / protection. Minimal guardrails framework, fully modular, teaches you to govern agents." width="900">

<br><br>

<h3>A practical, readable AI agent guardrails framework —<br>and a working example of how agents should be governed.</h3>

<a href="docs/">Documentation</a> · <a href="#-quickstart">Quickstart</a> · <a href="#-repo-structure">Repo Structure</a> · <a href="policies/">Policies</a> · <a href="#️-roadmap">Roadmap</a>

<br>

<a href="https://pypi.org/project/shugo/"><img src="https://img.shields.io/pypi/v/shugo?style=flat-square&color=A03A26" alt="PyPI"></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-A03A26?style=flat-square" alt="MIT License"></a>
<a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-native-0E1A2B?style=flat-square" alt="MCP native"></a>
<a href="https://github.com/aritraghosh01/shugo/releases/tag/v0.1.0"><img src="https://img.shields.io/badge/release-v0.1.0-1F6F4A?style=flat-square" alt="v0.1.0"></a>
<a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/PRs-welcome-1F6F4A?style=flat-square" alt="PRs welcome"></a>

</div>

<br>

---

<table>
<tr>
<td width="42%" valign="top">

<h2>🛡️ What is SHUGO?</h2>

<p>SHUGO is a guardrails-first framework for the agentic AI community.</p>

<p>It helps teams define policies, approval gates, tool access, evaluation, observability, and incident response in one repo.</p>

<p>It is designed to make AI agent behaviour <b>bounded, visible, and accountable</b>.</p>

<p>Responsible AI should not live in a slide deck. It should live in the same repo as the agent — expressed as code, enforced at runtime, and producing evidence by default.</p>

</td>
<td width="58%" valign="top">

<pre><code>shugo_repo  ->  shugo_policy  ->  shugo_runtime</code></pre>

<h2>📁 Repo Structure</h2>

<table>
<tr><td><code>src/shugo/</code></td><td>Proxy, policy engine, audit, CLI</td></tr>
<tr><td><code>policies/</code></td><td>Policy rules and standards</td></tr>
<tr><td><code>examples/</code></td><td>Runnable demo agents and configs</td></tr>
<tr><td><code>evaluations/</code></td><td>Tests, evals, and benchmarks</td></tr>
<tr><td><code>logs/</code></td><td>Runtime events and audit logs</td></tr>
<tr><td><code>docs/</code></td><td>Quickstart, policy guide, layers</td></tr>
<tr><td><code>guardrails.yaml</code></td><td>Guardrail configuration</td></tr>
<tr><td><code>incident-playbook.md</code></td><td>Incident response and recovery</td></tr>
<tr><td><code>README.md</code></td><td>Project overview and getting started</td></tr>
</table>

</td>
</tr>
</table>

<div align="center">

> **A guardrail should not merely tell an agent what it *should* do.**<br>
> **The system should enforce what the agent is *allowed* to do.**

</div>

---

<h2>🧱 Five Guardrail Layers</h2>

<table>
<tr>
<td width="20%" valign="top"><h4>👤 Identity<br>& Access</h4></td>
<td width="20%" valign="top"><h4>🗄️ Data<br>& Context</h4></td>
<td width="20%" valign="top"><h4>🔧 Action<br>& Autonomy</h4></td>
<td width="20%" valign="top"><h4>🛡️ Safety<br>& Resilience</h4></td>
<td width="20%" valign="top"><h4>🎖️ Governance<br>& Assurance</h4></td>
</tr>
<tr>
<td valign="top">Verify who and what can act, with least privilege and strong authentication.</td>
<td valign="top">Control what data enters the agent and how context is handled.</td>
<td valign="top">Restrict tools, enforce policies, and require approvals for high-risk actions.</td>
<td valign="top">Detect, block, and recover from unsafe behaviour and system failures.</td>
<td valign="top">Audit, evaluate, and report to ensure accountability and continuous trust.</td>
</tr>
<tr>
<td align="center"><sub>v0.1 · partial</sub></td>
<td align="center"><sub>v0.1 · partial</sub></td>
<td align="center"><sub>v0.1 · <b>full</b></sub></td>
<td align="center"><sub>v0.1 · partial</sub></td>
<td align="center"><sub>v0.1 · <b>full</b></sub></td>
</tr>
</table>

Layers ③ and ⑤ ship complete in v0.1. The others ship at the minimum depth needed to make those two credible, then deepen along the roadmap.

---

## ⚙️ How it works

SHUGO presents itself to your agent as a standard MCP server and sits between the agent and the tools it calls. Every `tools/call` is evaluated against a human-readable policy file before it reaches an upstream server. No protocol changes. No agent code changes.

```
┌──────────────┐   MCP    ┌───────────┐   MCP    ┌──────────────────┐
│  MCP client  │ ───────▶ │   SHUGO   │ ───────▶ │ Upstream MCP     │
│ (any agent)  │ ◀─────── │   guard   │ ◀─────── │ servers (n)      │
└──────────────┘          └─────┬─────┘          └──────────────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              guardrails    audit log    approval
                 .yaml      (JSONL)       channel
```

Works with Claude Desktop, Claude Code, Cursor, VS Code, and any framework with an MCP adapter — LangGraph, CrewAI, the OpenAI Agents SDK, n8n.

---

## ⚡ Quickstart

```bash
uvx shugo init      # scaffold a policy from your existing MCP config
uvx shugo serve     # start guarding
```

Point your MCP client at SHUGO instead of your servers:

```json
{
  "mcpServers": {
    "shugo": {
      "command": "uvx",
      "args": ["shugo", "serve", "--config", "guardrails.yaml"]
    }
  }
}
```

Your agent now sees only the tools policy allows, blocks on anything needing approval, and writes an audit record for every call it makes.

---

## 📜 Policy as code

The most important file in the project. Design target: **a risk lead can read it unaided, and a reviewer can diff it in a pull request.**

```yaml
version: "0.1"

defaults:
  decision: deny            # deny by default; allowlist upward
  on_error: deny            # fail closed

rules:
  - id: read-only-github
    match:
      server: github
      tool: ["get_*", "list_*", "search_*"]
    decision: allow

  - id: no-force-push
    description: Force push can destroy history irrecoverably
    match:
      server: github
      tool: push
      args: { force: true }
    decision: deny
    reason: Force push is prohibited for autonomous agents.
    controls: [OWASP-LLM06, NIST-AI-RMF-MANAGE-2.2]

  - id: ticket-write-needs-approval
    match:
      server: tickets
      tool: ["update_ticket", "close_ticket"]
    decision: escalate
    approval:
      channel: cli
      timeout_seconds: 300
      on_timeout: deny
    controls: [EU-AI-ACT-ART-14]
```

Deny by default. First match wins, top to bottom. Globs, not regex — readability is the constraint.

---

## 🧾 Evidence, not just logs

Enforcement without evidence is unauditable. Evidence without enforcement is theatre. SHUGO does both.

```bash
shugo evidence --framework owasp-llm --since 30d --out evidence/
```

Reads the audit log and produces a control-by-control bundle: which rules were in force, how often each fired, approval latency, exceptions, coverage gaps, and a hash-chain integrity check.

Framework mappings ship as data files sourced from **public** standards only — NIST AI RMF, EU AI Act, OWASP Top 10 for LLM Applications, and ISO/IEC 42001 control identifiers.

> **Scope note.** SHUGO produces evidence *about the guardrail layer*. It does not certify an organisation as compliant with any standard.

---

## 🧰 CLI

| Command | Purpose |
|---|---|
| `shugo serve` | Run the guard proxy |
| `shugo init` | Scaffold a starter policy from installed MCP servers |
| `shugo validate` | Lint and schema-check the policy file |
| `shugo explain` | Dry-run a call — see which rule fires and why |
| `shugo audit tail` / `verify` | Inspect the log, verify the hash chain |
| `shugo evidence` | Generate an evidence bundle |
| `shugo halt` | Kill switch — deny all calls immediately |

---

## 📦 Release notes — v0.1.0 (2026-07-30)

First release. Everything in the sections above is now real code you can install with `uvx shugo`.

**What ships:**

- **Guard proxy over stdio** — SHUGO speaks MCP to both your client and any number of upstream servers, namespaces tools as `<server>__<tool>`, and applies policy on every `tools/call`.
- **Policy engine** — deny-by-default, first-match-wins, `fnmatch` globs on server/tool, nested-equality on args. Decisions: `allow`, `deny`, `escalate`.
- **Human approvals** — file-drop queue at `~/.shugo/pending/` resolved by either `shugo approve --watch` (Rich TUI) or an opt-in local HTTP UI (`shugo serve --approvals http`).
- **Hash-chained audit log** — append-only JSONL, rolling SHA-256, NFC-canonical JSON, per-line `fsync`. `shugo audit verify` detects any post-hoc edit.
- **Evidence bundles** — `shugo evidence -f <owasp-llm|nist-ai-rmf|eu-ai-act|iso-42001>` produces a control-mapped report, policy snapshot, filtered audit-log window, and SHA-256 manifest.
- **`shugo init`** — reads Claude Desktop / Code / Cursor / VS Code MCP configs, enumerates upstream tools, writes a starter policy, prints the exact JSON snippet to paste.
- **Kill switch** — `shugo halt` denies everything until `shugo unhalt`.

**Quality:** 102 fast tests + 1 e2e test (real `@modelcontextprotocol/server-filesystem` via `npx`). CI on Python 3.11–3.13 × macOS / Ubuntu / Windows. All dependencies MIT / BSD-3 / Apache-2.0; no copyleft, no BSL.

Full changelog: [CHANGELOG.md](CHANGELOG.md) · GitHub release: [v0.1.0](https://github.com/aritraghosh01/shugo/releases/tag/v0.1.0)

---

## 🗺️ Roadmap

| Version | Theme | Status |
|---|---|---|
| **v0.1** | Guard proxy, policy engine, approvals, audit log, evidence packs | ✅ released 2026-07-30 |
| v0.2 | Layer ① depth — OAuth 2.1 / OIDC identity, per-principal policy, delegation scoping | planned |
| v0.3 | Layer ② depth — retrieval boundaries, context filters, memory access rules | planned |
| v0.4 | Layer ④ depth — injection detection, output validation, rollback | planned |
| v0.5 | Layer ⑤ depth — policy regression suites, adversarial harness | planned |
| v1.0 | Frozen policy schema, semantic versioning guarantee, plugin API | planned |

---

## 🤝 Contributing

SHUGO is built in public, and the contribution ladder is deliberately low to the ground:

**policy pack → scenario test → framework mapping → core**

A new policy pack is a self-contained YAML file. You do not need to read the codebase to ship one. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md) and the [good first issues](../../issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).

---

## 📄 License

Released under the [MIT License](LICENSE). Use it, fork it, adapt it to your own agent architecture — that is the point.

---

<div align="center">

<img src="assets/shugo-quote.png" alt="Capability makes an agent useful. Guardrails make it deployable." width="900">

<br>

<sub>守護 — <em>shugo</em>, to guard and protect.</sub>

</div>