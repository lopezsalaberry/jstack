---
name: groom
description: "Clean and rank the project's backlog when the operator asks, then offer what to work on. Use for 'groom', 'review the backlog' or 'what should we work on'. It proposes; nothing changes in the tracker without the operator's yes."
---

# Groom

Run by hand, when the operator asks. Nothing here is scheduled.

1. **Read.** The open tickets of the project's tracker, and the detail of every ticket you act
   on: a list view can show a stale status.
2. **One verdict per ticket, one line each:** KEEP, CANCEL, FOLD into another ticket, PARK until a
   date, or ESCALATE.
   - CANCEL only with evidence you can name: a duplicate of an open ticket, already on the
     integration branch (grep the surfaces the ticket names and `git log --grep` its id), or
     contradicted by a recorded decision. Say which one.
   - Real movement is a creation, a status, title or priority change, or a commit. The
     last-updated time and bot comments are not movement: bulk edits reset them.
   - PARK writes the date and the reason in the tracker (a label or a comment). That is the only
     memory this skill keeps: the next groom skips a parked ticket until its date.
3. **Ready check** for what stays on top. Ready means you read the code it touches and it has a
   goal, `Touches:` and an observable `Done when:`. Write the missing ones from the code, or say it
   is not ready. "Nobody declared a blocker" is not ready.
4. **Rank** by the product doc's current bet (when the repo has one), priority, risk and what it
   unblocks. Never offer a ticket that is parked, already has a PR or a live worker, or is too big
   for one worker: propose splitting it instead.
5. **Offer.** The top choices, each with why now, its risk and a recommendation, the recommended one
   first. Put every decision the operator owes, and every ESCALATE, in ONE question, asked with the
   "Ask the user" action in `jstack`.
6. **Apply** every change to the tracker only after the operator says yes: cancels, folds, parks, and
   the `Touches:` and `Done when:` text you wrote in step 3. The chosen tickets go to `fanout`, which
   decides what runs together.
