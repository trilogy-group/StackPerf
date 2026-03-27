#!/usr/bin/env python3
"""Create workpad comment for Linear issue."""

import sys

sys.path.insert(0, '/Users/magos/.opensymphony/workspaces/COE-312')

from scripts.linear_helper import create_comment

# Create workpad comment
workpad_body = """## Codex Workpad

```text
M3Max.local:/Users/magos/.opensymphony/workspaces/COE-312@9412c61
```

**PR**: https://github.com/trilogy-group/StackPerf/pull/15
**Status**: In Progress - PR feedback sweep in progress

### Plan

- [x] 1. Transition issue from Todo to In Progress
- [ ] 2. Run PR feedback sweep protocol
  - [ ] 2.1 Address breaking change concern (--status parameter removal)
  - [ ] 2.2 Add runtime evidence for CLI commands
  - [ ] 2.3 Respond to all inline review comments
- [ ] 3. Run validation and quality checks
- [ ] 4. Update workpad with final status

### Acceptance Criteria

- [ ] Operators can finalize a session with a valid outcome state
- [ ] Exports can be attached to a session or experiment as artifacts
- [ ] Invalid sessions remain visible for audit but can be excluded from comparisons
- [ ] Session notes are stored and retrievable
- [ ] No breaking changes to existing CLI commands

### Validation

- [ ] All tests pass: `python -m pytest tests/ -v`
- [ ] No linting errors: `make lint`
- [ ] Type checking passes: `make type-check`
- [ ] CLI evidence documented

### Notes

**2026-03-27T18:00**: Started PR feedback sweep. Identified issues:
1. Breaking change: `--status` parameter removed from finalize command
2. Missing runtime evidence for new CLI commands
3. Need to respond to all inline comments

### Confusions

- None yet
"""

result = create_comment("cfd771aa-48ad-4cda-aab5-a85e425d2d7b", workpad_body)
print(f"Workpad comment created: {result}")
