<!-- contextus:start -->
## Context (claude-contextus)

This project uses [claude-contextus](https://github.com/anthonypdawson/claude-contextus):
relevant patterns from `.claude/context/` are **retrieved and injected automatically**
on each prompt — you don't need to search for them. Injected blocks are tagged
`[contextus — …]`.

Context capture behavior is controlled by the per-prompt injected footer — follow
its instructions exactly (it may tell you to propose, write directly, or stay silent).
New context files live under `.claude/context/<category>/` and are embedded automatically.
<!-- contextus:end -->
