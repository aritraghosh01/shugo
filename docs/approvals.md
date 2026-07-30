# Approvals

When a rule with `decision: escalate` matches, the proxy blocks and waits for a human to say yes or no.

## The file-drop queue

SHUGO writes pending approvals to `~/.shugo/pending/<uuid>.json`. Verdicts land by moving the file:

```
~/.shugo/
├── pending/<uuid>.json      ← proxy writes; blocks on it
├── approved/<uuid>.json     ← operator moves to allow
├── denied/<uuid>.json       ← operator moves to deny
└── timeout/<uuid>.json      ← proxy moves on expiry
```

File moves are atomic (`os.replace`), so double-approve is naturally resolved — whoever wins the rename wins the decision.

## Sidecar TUI

In a second terminal:

```bash
uvx shugo approve --watch
```

The TUI polls `pending/` and prompts you per request. Keybindings: `a` approve, `d` deny, `s` skip.

## One-shot CLI

```bash
uvx shugo approve <request-id>
uvx shugo deny    <request-id> --note "not the right scope"
```

Useful for scripts and CI-style approvals.

## HTTP UI (opt-in)

```bash
uvx shugo serve --approvals http               # HTTP UI only
uvx shugo serve --approvals both               # TUI + HTTP UI
uvx shugo serve --approvals both --approvals-port 6247
```

Open <http://127.0.0.1:6247> — a single-page UI polls `/api/pending` every second and lets you Approve / Deny each request. Bound to `127.0.0.1` only; no authentication is applied because this is a local, single-user tool. Do not expose the port.

Both channels share the same file-drop backend, so a request queued while the browser is open can be resolved from the TUI (and vice versa).

## Timeout behavior

Each `approval:` block sets `timeout_seconds` and `on_timeout`:

- `on_timeout: deny` — fail closed. Recommended for destructive tools.
- `on_timeout: allow` — fail open. Only for low-risk tools where blocking would break the workflow.

Timeouts move the pending file to `~/.shugo/timeout/` for audit.

## Kill switch

```bash
uvx shugo halt
```

Writes `~/.shugo/HALT`. Every subsequent `tools/call` is denied immediately, before policy evaluation. `shugo unhalt` clears it.
