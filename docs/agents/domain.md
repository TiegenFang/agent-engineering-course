# Domain Docs

This repository uses a single-context domain-documentation layout.

## Before exploring or changing the project

- Read the root `CONTEXT.md` and use its defined terms throughout plans, issues, tests and implementation notes.
- Read the ADRs in `docs/adr/` that affect the area being changed.
- Read the current course plan and relevant source research when the task changes curriculum, content, exercises, validation or release policy.
- If a referenced document does not exist, proceed without inventing substitute terminology.

## Language and decisions

- Prefer the glossary's exact domain terms over near-synonyms it explicitly avoids.
- If a needed concept is genuinely absent, record the gap for domain-modeling rather than silently creating competing language.
- Surface conflicts with an existing ADR explicitly. Do not silently override an accepted decision.

## Layout

The root `CONTEXT.md` contains the ubiquitous language, while `docs/adr/` contains repository-wide architectural decisions. A `CONTEXT-MAP.md` or context-scoped ADR hierarchy is not used unless this repository later becomes a genuine multi-context monorepo.
