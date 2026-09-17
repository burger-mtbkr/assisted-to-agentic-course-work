# Module 4: Teaching Your Assistant New Skills

> Skills sit between context and tools — directed, indexed, progressively-disclosed processes that teach your assistant what to do, when to do it, and how.

## Overview

This module is the first stop on the **agent-enablement continuum**: context (the ether) → AGENTS.md (the index) → **skills (zoomed-in processes)** → tools (next module). Where Phase 1 was about giving your assistant the *what* (semantic context) and the *how* (procedural context and feedback loops), Phase 2 is about giving it the ability to *act*. Module 4 begins that arc by focusing on the **ergonomics of working with the codebase**: how skills make the assistant more efficient, set better expectations, and create supporting structures around the work the cohort already has in front of them.

By the end of Phase 2 (M4–M6) participants will have built **an agent harness around their codebase** — skills (M4) provide the process support, tools (M5) extend what the assistant can reach for, and the PAIR Agent (M6) assembles them. The skill you author in this module will become part of your PAIR Agent's repertoire, so we encourage you to pick something you'll actually want to use.

## Learning Objectives

By the end of this module, participants will:

1. Locate skills on the agent-enablement continuum (context → AGENTS.md → skills → tools) and explain why progressive disclosure is the connective tissue.
2. Distinguish skills from rules — what each is good for, when to reach for which.
3. Recognise that skills are a harness feature, and verify that their chosen harness supports them properly.
4. Identify candidate skills from their own development workflow, particularly during reflection at the end of a piece of work.
5. Author a working skill using the design-doc templates, supported by a skill-writing skill.
6. Evaluate skill quality using a small set of heuristics ("good description," "narrow scope," "idempotent") and recognise common anti-patterns.
7. Have at least one working skill supporting their Configuration API workflow that they will reuse with the PAIR Agent in Module 6.

## Module Structure

The lecture is a 15-section arc grouped into six clusters. Demo lands in section 14, exercise framing in section 15.

### 1. Where we are (Sections 1–2)

- **Journey checkpoint**: M1 collaboration foundations, M2 the WHAT (semantic context), M3 the HOW (procedural context), M4 zoomed-in process via skills, M5 preview (tools), M6 preview (PAIR Agent).
- **Learning objectives**: goal, takeaway, hope.

### 2. The continuum and progressive disclosure (Sections 3–4)

- **The continuum**: context (ether) → AGENTS.md (index) → skills (zoomed-in processes) → tools (next module). One-slide overview the rest of the deck explores.
- **Progressive disclosure as connective tissue**: the same pattern at every layer — agents load detail only when they need it.

### 3. Rules vs. skills, and where skills come from (Sections 5–6)

- **Rules vs. skills**: rules always loaded into context; skills loaded on invocation. The cleanest reason skills exist as a distinct mechanism.
- **Where skills come from**: emerging from the M3 wrap-up reflection cycle. Friction noticed → reflection → "next time I want this less manual" → skill. The "I went in cold" story as the worked example.

### 4. Anatomy and authoring (Sections 7–11)

- **Naming what we already do**: most software practice doesn't have SOPs. Articulating process is uncomfortable; that discomfort is the point.
- **Anatomy of a skill**: SKILL.md with frontmatter, body, optional script, optional bundled files.
- **What makes a description findable**: the discovery mechanism. Specific verb + situation, not "this skill helps with code."
- **What makes a skill good**: narrow scope, recipe-like body, idempotent, observable failures.
- **Anti-patterns**: vague names, aspirational bodies, hidden side effects, scope creep — with concrete bad/good pairs.

### 5. Harness, security, and evolution (Sections 12–13)

- **Script + LLM seam**: when scripts are worth the effort (deterministic facts the LLM can't know), when they aren't.
- **Harness as a feature + shortlist**: skills are a harness feature, not a model feature. Cline (VS Code, native since 3.48.0), Kilo Code, Claude Code (CLI), Codex CLI, Goose, optionally OpenCode. "Change if you want, verify if you're using something else, otherwise stay where you are."
- **Security & evolution sidebar**: the ~26% community-skill vulnerability finding (arXiv 2601.10338); supply-chain hygiene if you import community skills.

### 6. Demo and exercise (Sections 14–15)

- **Demo**: live authoring of a `start-work` skill against the Configuration API, using Anthropic's `skill-creator` skill (`anthropics/skills`, Apache 2.0).
- **Exercise + PAIR Agent connection**: pick one of four options (`start-work`, `draft-adr`, `end-of-day`/`start-of-day`, `assess-tests`) — or propose your own. What you build today, your agent uses in M6.

## Implementation Notes

### Materials

- Slide deck (`slides/slides.md`, MARP) — 15-section arc, ~90 minutes
- Skill design templates: `deliverables/examples/SKILL_DESIGN_TEMPLATE.md`, `deliverables/examples/SCRIPT_DESIGN_TEMPLATE.md`
- Worked design doc: `deliverables/examples/start-work-DESIGN.md`
- Reference skills (drop into your harness's skills directory to activate): `deliverables/examples/example-skills/`
  - `start-work/` — the demo skill (SKILL.md + script.sh)
  - `skill-creator/` — Anthropic's skill-authoring skill (Apache 2.0)
- Configuration API reference codebase: `deliverables/examples/config-service/`
- Exercise instructions: `deliverables/project/INSTRUCTIONS.md`
- Reflection prompts: `deliverables/project/INTEGRATE.md`

### Demo Environment

- A skills-supporting harness — Cline (VS Code, native since 3.48.0) or Claude Code (CLI) recommended; Codex CLI, Goose, or OpenCode also work
- Anthropic's `skill-creator` skill installed in that harness
- The Configuration API running locally (`make install && make up` from `deliverables/examples/config-service/`)
- Terminal in `deliverables/examples/`

### Key Outcomes

- A working skill, designed and authored in the cohort session, supporting a real piece of the participant's workflow
- A filled-in skill design doc that can be referenced when authoring future skills
- Practical familiarity with the script + LLM seam — when grounding via script is worth it, when it isn't
- A skill that becomes part of the participant's PAIR Agent repertoire in Module 6

### Further Resources

- Anthropic skill-creator: https://github.com/anthropics/skills/tree/main/skills/skill-creator
- Agent Skills specification: https://agentskills.io/specification
- Anthropic skill authoring best practices: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Cline skills documentation (native since 3.48.0)
- Community skill collections: `VoltAgent/awesome-agent-skills`, `heilcheng/awesome-agent-skills`
