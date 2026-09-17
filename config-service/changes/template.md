# Work Item Template

Copy this file to create a new numbered work item: `changes/NNN-name.md`
(e.g. `002-something.md`). See `context/WORKFLOW_STATUS.md` for the process
this file supports.

## Story Details

> As a [PERSONA], I want [FEATURE], so that [JUSTIFICATION]

### Notes

1-2 sentences of context: schema decisions, migration approach, which
endpoints are involved, anything that shapes the implementation.

### Acceptance Criteria (Given-When-Then)

Each task is roughly 1-3 commits and goes through all four stages on its
own.

#### Task 1: [Brief description]

- **Given**: [initial context/state]
- **When**: [action or trigger]
- **Then**: [expected outcome]
- **Status**: Not Started / In Progress / Complete

#### Task 2: [Brief description]

- **Given**:
- **When**:
- **Then**:
- **Status**: Not Started

*Add more tasks as needed.*

## Current Task Focus

- **Active task**: [task number and brief description]
- **Stage**: PLAN / BUILD & ASSESS / REFLECT & ADAPT / COMMIT & PICK NEXT
- **Last updated**: YYYY-MM-DD

### STAGE 1: PLAN

- **Test strategy**: what needs coverage (unit, integration, edge cases)
- **File changes**: which files, what kind of change

### STAGE 2: BUILD & ASSESS

- **Implementation progress**: what's done, what's left
- **Quality validation**: result of `npm run check` (see
  `context/ENV_SCRIPTS.md`) - must be fully clean before this stage is done

### STAGE 3: REFLECT & ADAPT

- **Process assessment**: what friction came up, what would help next time
- **Future task assessment**: do the remaining tasks above still make sense

### STAGE 4: COMMIT & PICK NEXT

- **Commit message**: (plain style - `"Module N: <what changed>"`, see
  `context/IMPLEMENTATION.md`)
- **README review**: which READMEs were checked/updated
- **Purge**: once committed, delete the STAGE 1-3 sections above - keep only
  the acceptance criteria (marked complete) and this "Current Task Focus"
  block updated for the next task
- **Next task**: which task above is next

---

### Quality checklist (every task, before COMMIT)

- [ ] `npm run test` passes
- [ ] `npm run lint` passes (dotnet build warnings-as-errors + eslint)
- [ ] `npm run format:check` passes (dotnet format + prettier)
- [ ] `npm run type-check` passes (tsc)
- [ ] Behavior verified against the Given-When-Then, not just green tests
