# Incident playbook

If an agent is about to do something you don't want it to do, or you suspect it already has, take these steps in order.

## 1. Stop the bleeding

```bash
uvx shugo halt
```

Writes `~/.shugo/HALT`. Every subsequent `tools/call` is denied at the top of the handler, before any policy evaluation. Zero further upstream calls will succeed until you `shugo unhalt`.

## 2. Preserve the record

The audit log at `~/.shugo/audit.log` is append-only and hash-chained. Do not edit it. Verify integrity first:

```bash
uvx shugo audit verify
```

If verify fails, someone (or something) has modified the log. The line number in the failure message identifies the first divergence.

## 3. Reconstruct what happened

```bash
uvx shugo audit tail -n 200
```

Each entry records `ts`, `server`, `tool`, `matched_rule_id`, `decision`, and (for escalated calls) `approver`. Filter with your normal JSON tools:

```bash
tail -n 500 ~/.shugo/audit.log | jq 'select(.decision=="deny")'
```

## 4. Snapshot evidence

Before you change the policy or clear the queue, capture a bundle:

```bash
uvx shugo evidence -f owasp-llm -s 24h -o incident-<date>/
```

The bundle includes `rules.yaml` (the policy in force), `audit-window.jsonl`, and `manifest.json` with per-file SHA-256s.

## 5. Tighten the policy

Edit `guardrails.yaml`, then dry-run the fix:

```bash
uvx shugo validate --config guardrails.yaml
uvx shugo explain -c guardrails.yaml -s <server> -t <tool> --args '<json>'
```

## 6. Resume

Clear any stuck approvals in `~/.shugo/pending/` if the operators are done triaging them (move to `denied/` to be safe), then:

```bash
uvx shugo unhalt
```

## 7. Postmortem

The bundle from step 4 plus a diff of `guardrails.yaml` before-and-after is the raw material for the postmortem doc.
