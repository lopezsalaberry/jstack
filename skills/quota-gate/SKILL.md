---
name: quota-gate
description: "Decide whether to start more work, and with which model, from remaining subscription quota. Use before every launch in fanout and when a model returns a quota or rate-limit error."
---

# Quota gate

Quota is the only thing that limits how many workers run. Settings used (see `jstack`):
`models`, `quota_probe`, `paid_fallback`.

## The probe contract

`<quota_probe> --provider <name>` exits 0 when that provider has quota, 1 when every
account is at 0%, and 2 when it does not know (no data, stale data, provider not
listed). The shipped `scripts/quota-probe` reads a plain file of
`<provider> <account> <percent>` lines; any command with the same contract works.

**Unknown is not exhausted.** On exit 2, go ahead and write "quota unknown for
`<provider>`" in the report. Do not invent scarcity from missing data.

**A reading is for this launch only.** Run the probe again before every launch, and write the command's own output in the
report. A result from earlier in the session, or "no quota source configured" from a probe that is not the one the
`quota_probe` setting names, is not data: a session that read "unknown" once kept calling a provider unknown for two days
while the configured probe said it was at 0%.

**Any other exit is a broken probe, not data.** Exit 64, or a usage text on stderr, means the probe did not
understand the call; a tool whose usage error exits 2 looks exactly like "unknown". Write "quota probe error"
in the report and carry on as unknown, but do not read it as data. `doctor` checks this.

**A refusal is the best data there is.** When starting a model fails for quota, rate limit,
authentication or availability, run `<quota_probe> --mark-exhausted <provider>` (for 60 minutes
by default; `--minutes N` changes it) and move to the next candidate at once. The mark makes the
probe answer 1 for that provider on this machine, so no other worker retries it. When a provider
answers again, `--clear <provider>` removes the mark.

**Silence is a refusal.** A model that was started and has produced nothing 2 minutes later is not slow, it is
not answering (a healthy start shows its first output within seconds): an exhausted account can hold a turn open without any error (a review once sat silent for
seven hours). Stop it, mark the provider with `--mark-exhausted <provider> --reason silent`, and take the next
candidate.

## Pick the model

1. `models` empty: use the model the harness already runs, and do not switch. If a
   quota or rate-limit error comes back, go to step 4.
2. Otherwise walk `models` in order. The first entry whose provider exits 0 or 2 is
   the one. Starting a worker on a different provider than the current thread means
   **writing `RUNSTATE.md` first** (ticket, branch, state, next step) and starting the
   new worker from it with a fresh brief. Never switch silently mid-thread. Some
   harnesses cannot move a running thread: then the new worker is a new thread that
   reads `RUNSTATE.md`.
3. Use the strongest model in the list only for design work or when the operator asks;
   workers default to the first entry.
4. Every provider in `models` exits 1, or returns a quota error: commit work in
   progress, push, and report `WAITING <resume condition>`. The condition is "the
   probe exits 0 or 2 for any provider in `models`". This is the only case where the
   stack waits. Never fail a ticket for quota.

## Paid fallback

Pay-per-token routes or API-credit keys are off. They apply only when `paid_fallback`
names a provider and a daily cap, or when the operator asks for that task. Stop at the
cap and report `WAITING`.
