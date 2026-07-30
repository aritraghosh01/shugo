# Evidence bundles

SHUGO turns the hash-chained audit log into a control-mapped evidence bundle you can hand to a risk lead, auditor, or CI job.

```bash
uvx shugo evidence -f owasp-llm -s 30d -o evidence/
```

Available frameworks:

| Flag | Framework | Source |
|---|---|---|
| `owasp-llm` | OWASP Top 10 for LLM Applications (2025) | <https://genai.owasp.org/llm-top-10/> |
| `nist-ai-rmf` | NIST AI Risk Management Framework 1.0 | <https://www.nist.gov/itl/ai-risk-management-framework> |
| `eu-ai-act` | EU AI Act (2024) | <https://artificialintelligenceact.eu/> |
| `iso-42001` | ISO/IEC 42001:2023 | <https://www.iso.org/standard/81230.html> |

## `--since`

Accepts a relative duration (`Nd`, `Nh`, `Nm`) or an absolute ISO date/datetime.

## Bundle contents

Each run writes `evidence/<framework>-<YYYYMMDD-HHMMSS>/` containing:

- **`report.md`** — per-control table (matched rules, fires, approvals, denies), coverage gaps, integrity result.
- **`rules.yaml`** — snapshot of the `guardrails.yaml` in force during the window.
- **`audit-window.jsonl`** — filtered audit entries.
- **`manifest.json`** — SHA-256 of every file in the bundle plus the audit log's `shugo audit verify` result.

## Scope

> **SHUGO produces evidence *about the guardrail layer*. It does not certify an organisation as compliant with any standard.**

The framework mappings ship as data files authored by the SHUGO project from public sources — they reference control identifiers only and do not reproduce copyrighted control text. Use the bundles as inputs to your compliance process, not as its output.
