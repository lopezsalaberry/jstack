---
name: quota-gate
description: "Decide whether to start more work, and with which model, from remaining subscription quota. Use before every launch in fanout and when a model returns a quota or rate-limit error."
---

> jstack, operator rule (2026-11-01): concurrency is limited only by subscription quota; when Claude is out, fall back to Codex with a handoff, never wait.

# Quota gate

Before starting a worker, run `$JSTACK_QUOTA_PROBE`. It prints one line per
Hub subscription account: `<provider> <account> <percent remaining>`.
`$JSTACK_QUOTA_PROBE --model <id>` exits 0 when that model's provider has quota, 1 when not.

Pick the model in this order:

1. Claude above 0% on any account: `claudeAgent` / `claude-sonnet-5-5`
   (`claude-opus-5-5` only for design, Open Pencil, or when the operator asks).
2. Claude at 0% and Codex above 0%: `codex` / `gpt-6.1-sol`. Write a
   `session-handoff` first (ticket, branch, state, next step) and start the
   Codex worker from it. Do not wait for Claude.
3. Both at 0%, or a quota error on both: pause. Commit work in progress, stop
   at a safe point, resume when either provider returns.

Never use OpenRouter or the Anthropic credits key for routine waves; only when
the operator asks explicitly for that task. The probe hides them unless `--include-paid`.
