---
name: quota-gate
description: "Decide whether to start more work from remaining model quota. Use before every launch in fanout and when a model returns a quota or rate-limit error."
---

> New in jstack, for the operator's rule: concurrency is limited only by quota, pause at zero, never divert.

# Quota gate

Before starting a worker, run `$JSTACK_QUOTA_PROBE`, set per machine. It
prints one line per account: `<account> <percent remaining>` for the default model.

- Any account above 0%: launch.
- 0% on every account, or a quota or rate-limit error: pause. Commit work in
  progress, stop at a safe point, resume when quota returns.

Never switch to another model or provider to keep going.
