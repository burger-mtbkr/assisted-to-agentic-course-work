# Module 3: Feedback Loops and Dynamic Context

> Using structured context and runtime signals to guide assistant collaboration

This is a good reflection question for this module: Did you experience flow during this process? Could you have? Do you have a sense of what got in the way?

## Overview

This module deepens the practice of AI-assisted development by introducing **dynamic context feedback loops** — using runtime signals like linter output, type checks, and tests to close the loop between generation and validation. Participants will learn how to design prompts that self-verify, structure their repositories for assistant-friendly automation, and integrate simple toolchains to create a higher-precision development experience.

We'll explore how tools like `make`, linters, type checkers, and test runners can form the basis for assistant-invoked feedback loops. By the end of this module, participants will have enhanced their configuration service with self-validating workflows and built the foundations for tool-augmented collaboration — paving the way for Phase 2.

## Learning Objectives

By the end of this module, participants will:

1. Understand and implement dynamic context via feedback-driven prompting
2. Use tool outputs (lint, type errors, test failures) as inputs for iterative assistant use
3. Structure Makefile targets and validation scripts to support assistant workflows
4. Apply "trust-but-verify" prompting patterns to improve code reliability
5. Prepare codebases for tool-assisted and agentic workflows

## Module Structure

### 1. Introducing Dynamic Context

- **Static vs. Dynamic Context**:
  - Why static docs alone aren't enough
  - Using runtime feedback (errors, test failures) as new input
  - The value of self-checking workflows

- **Examples of Dynamic Context in Practice**:
  - Linting and formatting errors
  - Type-checking violations
  - Test failures and CI output

### 2. Feedback-Driven Prompting

- **Self-Verifying Prompt Patterns**:
  - Structuring prompts with validation steps
  - Iterating until output passes all checks
  - Prompt recipes: “Write, run, revise”

- **Developing Prompt Fluency**:
  - Creating guardrails with assistant instructions
  - Using assistants to analyze and respond to tool output
  - Avoiding over-prompting: when enough context is enough

### 3. Tool-Aware Repositories

- **Makefile Interfaces as Assistant APIs**:
  - Designing make targets like `make check`, `make lint`, `make test`
  - Creating discoverable, assistant-friendly command surfaces

- **Creating Assistant-Compatible Scaffolding**:
  - Folder structure conventions
  - File layout predictability
  - Reducing ambiguity in assistant-controlled tasks

- **Trust-But-Verify Development**:
  - Running assistant-generated code through automated validation
  - Enforcing clean runs as a baseline: no warnings, no skips
  - Building trust in iterative outputs

### 4. Building Precision Workflows

- **Assistant-Oriented Quality Loops**:
  - Using runtime outputs as prompt inputs
  - Automating context extraction and cleanup
  - Establishing high-fidelity refactoring and generation flows

- **Preparing for Agentic Workflows**:
  - Identifying parts of your development flow that can be delegated
  - Logging failure modes for future reference
  - Creating traceable audit trails of assistant decision-making

### 5. Hands-on Exercise: Tool-Integrated Context Feedback Loop

- **Exercise Overview**:
  - Enhance your config service with dynamic validation
  - Integrate `make` targets for linting, typing, testing
  - Create self-verifying prompt patterns for assistant collaboration

- **Exercise Steps**:
  - Add `make check`, `make lint`, and `make test` targets
  - Use assistants to generate and refine code using validation outputs
  - Refactor existing features using the dynamic loop
  - Document your process and include validated patterns in your context library

## Implementation Notes

### Materials

- Slide deck: Dynamic context and validation-driven prompting
- Makefile template and command patterns
- Prompt structure examples and templates
- Config service starter codebase with test suite and linter config

### Demo Environment

- Dockerized environment with make, flake8, mypy, and pytest pre-installed
- Preconfigured VSCode with AI tools and context helpers
- Config service project scaffold from Module 2

### Key Outcomes

- Completed config service enhanced with validation-driven development
- Repository with clean Makefile targets and dynamic feedback loops
- Prompt library with feedback-aware examples
- Ready-to-extend scaffolding for tool-aware assistant workflows
