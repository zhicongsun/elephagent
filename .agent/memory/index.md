# Agent Memory Index

This directory is the platform-neutral source of truth for coding agents working in this repository.

## How Agents Should Use This

- Read this file first when starting work in the repository.
- Search the rest of `.agent/memory/` when architecture, workflows, decisions, pitfalls, or terminology matter.
- Add durable notes with `python3 agent_kit.py remember "..."`.
- Do not store secrets, tokens, credentials, or private machine paths in shared memory.

## Current Project Notes

- The shared memory and tool layer is managed by `agent_kit.py`.
- Generated platform files are derived from `.agent/`.
