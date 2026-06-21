---
name: branch-protection-workflow
description: Vector Inspector requires PRs for all changes - never push directly to master
metadata:
  type: decision
  tags: [git, workflow, branch-protection, ci]
  created: 2026-06-21
---

# Branch Protection Workflow for Vector Inspector

## Decision

**Never push directly to master** in vector-inspector. All changes must go through feature branches and pull requests.

## Why

Vector Inspector has branch protection enabled on master to:
- Maintain code quality through review process
- Ensure CI passes before merge
- Keep a clean, documented history
- Allow team visibility on changes

## How to Apply

### Standard Workflow (Always)

1. **Create feature branch** from master:
   ```bash
   git checkout master
   git pull origin master
   git checkout -b fix/your-feature-name
   ```

2. **Make changes and commit:**
   ```bash
   git add <files>
   git commit -m "descriptive message"
   ```

3. **Push branch and create PR:**
   ```bash
   git push origin fix/your-feature-name
   gh pr create --title "..." --body "..."
   ```

4. **Wait for review and CI** before merge

### What NOT to Do

❌ `git push origin master` - Direct push rejected by branch protection
❌ `git commit -am "quick fix" && git push` - Bypasses review process
❌ Pushing "small" or "urgent" fixes directly - use PR even for one-line changes

## Exceptions (Rare)

**Urgent CI/workflow fixes** blocking releases MAY be pushed directly to master:
- ⚠️ **ALWAYS ASK FIRST** - don't assume urgency
- Examples: broken GitHub Actions syntax, release workflow failures
- User will explicitly say "it's ok" for the specific case
- Still prefer PR if time allows

**Today's exception:** Two CI workflow fixes were pushed directly (tag resolution bug, nuitka compression) during active installer build emergency. User approved with "I suppose for this it's ok" - but this is the exception, not the rule.

## Edge Cases

**Q: Small typo in docs?**
→ Still use PR. It's fast and maintains consistency.

**Q: Reverting a broken commit?**
→ Use PR unless production is actively broken and user approves.

**Q: GitHub Actions workflow is broken and blocking release?**
→ Ask first. If urgent and approved, push directly. Otherwise PR.

**Q: Multiple related fixes across different concerns?**
→ One PR per logical change. Don't bundle unrelated fixes.

## Related Patterns

- [[pr-review-process]] (if exists)
- [[git-commit-style]] (if exists)

## Reminder for Claude

When user asks to "fix X" or "change Y" in vector-inspector:
1. ✅ Create feature branch
2. ✅ Make changes
3. ✅ Commit and push to branch  
4. ✅ Create PR
5. ❌ Never push to master without explicit approval

If tempted to push to master, **ask first**.
