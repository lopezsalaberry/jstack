---
name: groom
description: "Clean and rank the project's backlog when the operator asks, then offer what to work on. Use for 'groom', 'review the backlog' or 'what should we work on'. It proposes; nothing changes in the tracker without the operator's yes."
---

# Groom

Run by hand. Nothing here is scheduled.

1. **Read.** The open tickets of the project's tracker, and the detail of every ticket you act
   on: a list view can show a stale status. Name any unverified; no verdict.
2. **One verdict per ticket, one line each:** KEEP, CANCEL, DELIVERED, SHIPPED, FOLD into another ticket, PARK
   until a date, or ESCALATE.
   - CANCEL only with evidence you can name: a duplicate of an open ticket, or contradicted by a
     recorded decision. Say which one.
   - DELIVERED is work already on the integration branch: its commit is an ancestor of it (find it
     with `git log --grep` on the id, confirm with `git merge-base --is-ancestor`). Move it to review
     with the commit and PR in a comment, never to canceled: it is done only when the operator accepts.
     A commit naming the ticket does not prove its criteria; say what you did not check.
   - SHIPPED is a ticket in review whose commit is in a published release (`git tag --contains`). Propose done, with the version and
     SHA in a comment; the operator's yes to the list is the acceptance.
   - Real movement is a creation, a status, title or priority change, or a commit; last-updated time and bot comments are not (bulk edits reset them).
   - PARK writes the date and the reason in the tracker (a label or a comment). The next groom skips it until then.
3. **Ready check** for what stays on top. Ready means you read the code it touches and it has a
   goal, `Touches:` and an observable `Done when:`. Write missing ones from the code, or say it is not ready. "Nobody declared a blocker" is not ready.
4. **Rank** by the product doc's current bet (if any), priority, risk and what it
   unblocks. Never offer a parked ticket, one with a PR or a live worker, or one too big
   for one worker: propose splitting it.
5. **Offer.** The top choices, each with why now, its risk and a recommendation, the recommended one
   first. Put every decision owed, and every ESCALATE, in ONE question, asked with the
   "Ask the user" action in `jstack`.
6. **Apply** every change to the tracker only after the operator says yes: cancels, folds, parks, moves to review or done, and
   the `Touches:` and `Done when:` text you wrote in step 3. The chosen tickets go to `wave`.
