# Rewording the skills' prohibitions as positive instructions

**What:** rewrite `ticket`, `review` and `wave` so "never / do not" becomes what to do, keeping "never" only for hard
limits. The idea is that naming a forbidden action primes it.

**Why not:** measured on 2026-11-20, 24 runs, 4 per scenario per arm. Both versions scored 54 of 56 checks with the
same single failure. The rewrite took longer and cost more in every proof run (47 s against 33-35 s). No agent
loaded `review` or `wave`. There is no failure it fixes. Branch `exp/positive-1120` was kept local.

**Reopens when:** a session shows an agent doing a thing because a skill forbade it.
