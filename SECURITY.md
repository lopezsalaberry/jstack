# Security

Report a vulnerability privately through GitHub: the repository's **Security** tab, then
**Report a vulnerability**. Please do not open a public issue for it. Expect an acknowledgement
within a few days.

What is in scope:

- `install.sh` writes symlinks and moves same-name items into a backup folder; it must never delete
  anything that is not a jstack link or write outside the target skill folders.
- `pr-wait` and the skills run `gh` with the user's token. They must not print it, post it, or send
  it elsewhere.
- Skills grant autonomy (merge, force-push to a ticket's own branch). Any way to make a skill act
  outside those limits, or around branch protection, is in scope.

Out of scope: the behavior of the agent harness or model that runs the skills.
