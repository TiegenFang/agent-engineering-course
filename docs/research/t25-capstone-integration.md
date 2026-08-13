# T25：双轨结课集成实现记录

## Scope

T25（issue #26）把公共练习仓库的共同能力证据接到科研结课轨道与企业结课轨道之一，验证“不同交付视角、同一能力目标和同一证据边界”的离线接缝。它不重复 T23 科研轨道或 T24 企业轨道，也不把真实工具现场验证伪装成课程完成。

## Deterministic seam

- lesson: `t25-capstone-integration`
- experiment: `telemetry-capstone-integration-v1`
- evidence: `agent-engineering-course/evidence` v1
- tracks: `research`, `enterprise`
- faults: `none`, `missing-core`, `unsafe-side-effect`, `incomplete-delivery`
- checks: 12 fixed IDs covering scope, Context/Memory, Skill/MCP boundary, core evidence, validation, migration, delivery, privacy, version and offline status
- public JSON excludes paths, source text, Issue/PR bodies, prompts, tool payloads, credentials, raw telemetry and hidden reasoning

## Source/contract note

The course content contract and source ledger are maintained as shared registries by the integrating branch. The registry entry should reference this file and the original T23/T24/T29 course materials, with no copied third-party assets. The page and lab are original course assets; no live OpenAI, Anthropic, Codex, Claude Code, MCP or GitHub call is made by the fixture.

## Validation boundary

The Python runner, checker and Node/browser fixture are intended for Windows 11 + PowerShell 7. A passing offline document proves only the deterministic evidence mapping. It does not prove a live Coding Agent run, a GitHub Issue-to-PR, an API request, a remote MCP transport, billing, permissions, or production data acceptance.
