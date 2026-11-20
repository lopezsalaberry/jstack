# Fixing causes nobody saw

**What:** widening a fix to cover the causes that could produce a failure (stale permission entries, signatures,
copies in Downloads) instead of the one that was observed.

**Why not:** the failure went away when the app was restarted: every hypothesis was false and the ticket would have
built code for a cause that never happened.

**Reopens when:** never as a rule. Ask for the cheapest test first (restart, try again), then scope the fix.
