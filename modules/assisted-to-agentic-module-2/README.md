# Module 2: Building a Context Framework

> Your assistant's memory starts fresh every session. This module is about fixing that.

## Overview

Static documentation becomes your secret weapon when you write it for an AI audience. In this module you'll build a context framework: a small set of documents that keep your assistant sharp across sessions, eliminate repetitive explanations, and make complex changes feel routine.

We'll build the framework incrementally against the Config API from Module 1 — starting with project identity and architecture, then adding workflow, conventions, and domain knowledge. By the end you'll have a reusable asset and a clear sense of when context engineering is worth the effort and when it isn't.

## Learning Objectives

By the end of this module, participants will:

1. Identify the role of the components of a context framework
2. Implement a context framework for structured AI context management
3. Experience the results of both effective and ineffective context
4. Experience collaborative task management with an assistant 

## Module Structure

### 1. Advanced Conversational Patterns

- **Multi-turn Interaction Strategies**:
  - Progressive refinement techniques
  - Context management across conversation turns
  - Handling conversation drift and recovery

- **Conversation Design Principles**:
  - Clarity and specificity in requests
  - Effective follow-up questioning
  - Balancing direction and exploration

### 2. AI Tool Landscape

- **Tool Categories and Capabilities**:
  - IDE integrations (Cursor, Cline, RooCode, Windsurf)
  - Standalone assistants (Claude Code, Cursor)
  - Specialized coding tools (integrations with pipelines, PRs, etc)

- **Selection Criteria**:
  - Task appropriateness
  - Integration requirements
  - Learning curve considerations
  - Cost and accessibility

- **Hands-on Tool Exploration**:
  - Setting up and configuring key tools
  - Basic usage patterns
  - Tool-specific strengths and limitations

### 3. Context Framework Implementation

- **Introduction**:
  - Core philosophy: minimum documentation for maximum AI precision
  - Framework components: workflow, architecture, implementation, domain knowledge
  - Balancing comprehensiveness with maintainability

- **Document Types and Structure**:
  - WORKFLOW_STATUS.md: Development processes and current project state
  - ARCHITECTURE.md: System design, patterns, and technical decisions
  - IMPLEMENTATION.md: Code conventions, examples, and quality standards
  - DOMAIN_GLOSSARY.md: Business terms, concepts, and context
  - ENV_SCRIPTS.md: Setup, deployment, and operational procedures

- **Context Engineering Principles**:
  - Relevance and specificity for task precision
  - Progressive disclosure of complexity
  - Consistency in terminology and structure
  - Validation and iterative refinement

### 4. Architecture and Planning with AI

- **Architecture Decision Records (ADR) Generation**:
  - Collaborative decision-making with AI
  - Documenting architectural choices effectively
  - Maintaining design consistency through ADRs

- **System Design Conversations**:
  - Exploring design alternatives conversationally
  - Evaluating trade-offs with AI input
  - Documenting design decisions and rationales

- **Implementation Planning**:
  - Breaking down features into implementable components
  - Estimating complexity and effort
  - Creating development roadmaps with AI assistance

### 5. Context Quality and Management

- **Context Creation Techniques**:
  - Extracting context from existing documentation and code
  - Generating context collaboratively with AI assistance
  - Context validation through development testing
  - Iterative refinement based on friction detection

- **Context Management Strategies**:
  - Versioning and updating approaches across development cycles
  - Modularizing context for reuse and specialization
  - Maintaining context accuracy throughout project evolution
  - Cross-session context persistence and retrieval

- **Document-Driven Development Patterns**:
  - Using documentation as implementation driver
  - Specifications that AI can effectively interpret
  - Maintaining alignment between documentation and code
  - Context-first feature planning and execution

### 6. Hands-on Exercise: Building a context framework for Config API

- **Exercise Overview**:
  - Creating comprehensive context documentation for the Configuration API Service
  - Adding complex features using document-driven development
  - Experiencing precision improvements through rich context

- **Exercise Steps**:
  - Establishing a structure and initial documentation
  - Implementing feature flags and user-specific configuration inheritance
  - Building versioning and rollback capabilities using context-driven development
  - Documenting architectural decisions and implementation patterns
  - Validating context effectiveness through development friction reduction

### 7. What's Next

- **Preview of Module 3**: Validating context framework through new features/endpoints and new service creation
- **Preparation Tasks**: Complete documentation, practice context-driven feature development
- **Resources**: Context templates, context engineering best practices, document structure examples

## Implementation Notes

### Materials

- Slide deck for conceptual sections
- Conversation templates and examples
- ADR templates and examples
- Sample code for the enhanced Configuration API Service

### Key Outcomes

- Complete a context framework for Configuration API Service
- Enhanced Configuration API with complex features built through document-driven development
- Demonstrated precision improvements through structured context
- Personal context engineering practices and quality assessment frameworks
