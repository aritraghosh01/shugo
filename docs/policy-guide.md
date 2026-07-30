# Policy guide

A SHUGO policy is a single YAML file. Design target: a risk lead can read it unaided, and a reviewer can diff it in a pull request.

## Anatomy

```yaml
version: "0.1"

defaults:
  decision: deny            # fall-through: what to do when no rule matches
  on_error: deny            # what to do when an upstream crashes or args are malformed

upstreams:                  # every MCP server SHUGO is willing to forward to
  github:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-github"]
    env: {}

rules:                      # evaluated top-to-bottom, first match wins
  - id: read-only-github
    match:
      server: github
      tool: ["get_*", "list_*", "search_*"]
    decision: allow

  - id: no-force-push
    description: Force push can destroy history irrecoverably.
    match:
      server: github
      tool: push
      args:
        force: true
    decision: deny
    reason: Force push is prohibited for autonomous agents.
    controls: [OWASP-LLM06, NIST-AI-RMF-MANAGE-2.2]

  - id: write-needs-approval
    match:
      server: github
      tool: "*"
    decision: escalate
    approval:
      channel: cli
      timeout_seconds: 300
      on_timeout: deny
    controls: [EU-AI-ACT-ART-14]

redact:                     # dotted paths of secret-bearing fields
  - password
  - headers.authorization
```

## Match semantics

- **`server`** and **`tool`** — string or list of strings. Each item is a `fnmatch` glob (`*`, `?`, `[abc]`). Both must match if given.
- **`args`** — nested equality. Every key you specify must exist in the call arguments with an equal value; extra keys in the call are fine. No regex in v0.1.
- Rule order is precedence. First match wins.
- If no rule matches, `defaults.decision` applies.

## Decisions

| Decision | What happens |
|---|---|
| `allow` | Forward to the upstream. Audit-log the call. |
| `deny` | Return an `McpError` to the client. Don't touch the upstream. Audit-log the deny. |
| `escalate` | Write a pending approval; block until an operator approves, denies, or the timeout fires. Requires an `approval:` block. |

## Approvals

For `decision: escalate`, an `approval:` block is required:

```yaml
approval:
  channel: cli              # only channel in v0.1
  timeout_seconds: 300
  on_timeout: deny          # deny (fail-closed) or allow (fail-open)
```

See [approvals.md](approvals.md) for the file-drop queue and TUI / HTTP UI channels.

## Controls

Every rule may list any number of `controls:` — free-form identifiers used by `shugo evidence` to compute per-control coverage. Recommended prefixes:

- `OWASP-LLM01` … `OWASP-LLM10`
- `NIST-AI-RMF-<function>-<subcategory>` e.g. `NIST-AI-RMF-MANAGE-2.2`
- `EU-AI-ACT-ART-<n>` e.g. `EU-AI-ACT-ART-14`
- `ISO-42001-<clause>` e.g. `ISO-42001-A.7.4`

## Redaction

Anything in `redact:` is replaced with `"***"` in the stored audit entry **before** the hash is computed, so log and hash agree.

## Validating

```bash
shugo validate --config guardrails.yaml
shugo explain -c guardrails.yaml -s github -t push --args '{"force": true}'
```

`explain` shows which rule fires and why, without contacting any upstream.
