# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**MANDATORY: Read [`AGENT_GUIDE.md`](AGENT_GUIDE.md) before responding to ANY user message.**

## Common Commands

### Setup and Installation
```bash
# Initial setup (creates venv, installs dependencies, sets up Remotion)
make setup

# Install only Python dependencies
make install

# Install development dependencies (includes pytest)
make install-dev

# Install GPU support (for local video generation)
make install-gpu
```

### Testing
```bash
# Run all tests
make test

# Run only contract tests (no API keys needed)
make test-contracts

# Run a single test file
.venv/bin/python -m pytest tests/contracts/test_pipeline_contracts.py -v

# Run a specific test function
.venv/bin/python -m pytest tests/contracts/test_pipeline_contracts.py::test_pipeline_name -v
```

### Utilities
```bash
# Check available tools and providers
make preflight

# Render zero-key demo videos
make demo

# List available demos
make demo-list

# Validate HyperFrames runtime
make hyperframes-doctor

# Refresh HyperFrames npx cache
make hyperframes-warm

# Lint core Python files
make lint

# Clean Python cache files
make clean
```

## Architecture Overview

OpenMontage is an **agent-first, instruction-driven video production system**. The AI agent IS the orchestrator—there is no Python orchestration code. Python provides only tools and persistence; all creative decisions, workflow logic, and quality gates live in YAML manifests and Markdown skill files.

### Three-Layer Knowledge Architecture

```
Layer 1: tools/ + pipeline_defs/     "What exists" — executable capabilities + orchestration
Layer 2: skills/                     "How to use it" — OpenMontage conventions and quality bars  
Layer 3: .agents/skills/             "How it works" — external technology knowledge packs
```

Each tool declares which Layer 3 skills it relies on via the `agent_skills` field. The agent reads Layer 1 to know what's available, Layer 2 to know how OpenMontage wants it used, and Layer 3 for deep technical knowledge when needed.

### Core Workflow

Every video production follows a pipeline-driven state machine:
```
research → proposal → script → scene_plan → assets → edit → compose
```

Each stage has:
- A **pipeline manifest** (YAML in `pipeline_defs/`) defining stages, tools, review criteria, and approval gates
- A **stage director skill** (Markdown in `skills/pipelines/<pipeline>/<stage>-director.md`) teaching the agent HOW to execute that stage
- **Meta skills** (in `skills/meta/`) for cross-cutting concerns like review and checkpointing

### Key Directories

- **`tools/`** — Python tools (the agent's hands). All inherit from `BaseTool` in `base_tool.py`. Organized by capability: `video/`, `audio/`, `graphics/`, `enhancement/`, `analysis/`, `avatar/`, `subtitle/`, `character/`
- **`pipeline_defs/`** — YAML pipeline manifests (the agent's playbook). Each pipeline declares stages, required tools, review focus, and human approval gates
- **`skills/`** — Markdown skill files (the agent's knowledge). Organized as:
  - `pipelines/` — Per-pipeline stage director skills
  - `creative/` — Creative technique skills
  - `core/` — Core tool usage skills
  - `meta/` — Reviewer, checkpoint protocol, onboarding
- **`schemas/`** — JSON Schemas for contract validation (artifacts, checkpoints, pipelines, styles, tools)
- **`styles/`** — Visual style playbooks (YAML) defining typography, color, motion, audio profiles
- **`remotion-composer/`** — React/Remotion video composition engine (Node.js)
- **`lib/`** — Core infrastructure: config loading, checkpoints, pipeline loader, scoring, delivery promise validation
- **`tests/`** — Contract tests, QA integration tests, eval harness
- **`.agents/skills/`** — Layer 3 technology knowledge packs (vendor-specific skills, API documentation)

### Tool Registry and Discovery

Tools are discovered dynamically via `tools/tool_registry.py`. The registry provides:
- `support_envelope()` — Full capability report (every tool's contract)
- `provider_menu()` — Grouped available/unavailable per capability
- `provider_menu_summary()` — Human-ready rollup (use this first)
- `capability_catalog()` — Tools grouped by capability family
- `provider_catalog()` — Tools grouped by provider

Three selector tools abstract multi-provider capabilities:
- `tts_selector` — Routes to all TTS providers
- `image_selector` — Routes to all image generation providers  
- `video_selector` — Routes to all video generation providers

### Composition Runtimes

`video_compose` supports three render engines, chosen at proposal time and locked in `edit_decisions.render_runtime`:
- **FFmpeg** — Video-only cuts, concat, trim, subtitle burn (always available)
- **Remotion** — React-based composition: spring-animated scenes, text cards, charts, word-level captions (requires Node.js)
- **HyperFrames** — HTML/CSS/GSAP composition: kinetic typography, product promos, SVG character rigs (requires Node.js ≥ 22)

### Project Workspace Convention

Every production creates a project workspace under `projects/<project-name>/`:
```
projects/<project-name>/
├── artifacts/          # JSON artifacts from each stage
├── assets/
│   ├── images/         # Generated images (PNG)
│   ├── video/          # Generated video clips (MP4)
│   ├── audio/          # Narration + final mix (MP3/WAV)
│   ├── music/          # Background music (MP3)
│   └── subtitles.srt   # Generated subtitles
└── renders/
    └── final.mp4       # Final rendered video
```

### Critical Patterns

- **Pipeline manifests are declarative YAML** — No Python orchestration code. The agent reads manifests and follows stage director skills.
- **Tools inherit from `BaseTool`** — All tools implement `execute(params_dict)` returning `ToolResult` with `.success`, `.data`, `.error`.
- **Canonical artifacts** — Each stage produces one canonical artifact (`brief`, `script`, `scene_plan`, `asset_manifest`, `edit_decisions`, `render_report`) validated against JSON schemas.
- **Checkpoints** — Stored in `pipelines/<project_id>/checkpoint_<stage>.json`. Status can be `completed`, `failed`, `awaiting_human`, or `in_progress`.
- **Cost tracking** — `tools/cost_tracker.py` manages budget governance: estimate → reserve → reconcile. Supports `observe`, `warn`, and `cap` modes.
- **Scored provider selection** — Every tool selection runs through a 7-dimension scoring engine (task fit, quality, control, reliability, cost, latency, continuity).

### Available Pipelines

- `animated-explainer` — Topic to fully generated explainer (production)
- `talking-head` — Footage-led speaker videos (beta)
- `screen-demo` — Screen recordings and walkthroughs (production)
- `clip-factory` — Many clips from one long source (beta)
- `podcast-repurpose` — Podcast highlights and derivatives (beta)
- `cinematic` — Trailer, teaser, and mood-led edits (production)
- `animation` — Motion-graphics and animation-first videos (production)
- `character-animation` — Local rigged cartoon characters (beta)
- `hybrid` — Source footage plus support visuals (production)
- `avatar-spokesperson` — Presenter-led avatar videos (production)
- `localization-dub` — Subtitle, dub, and translated variants (beta)
- `documentary-montage` — Real-footage documentary from free stock (production)

### Style Playbooks

Visual style is controlled via YAML playbooks in `styles/`:
- `clean-professional` — Corporate, educational, SaaS
- `flat-motion-graphics` — Social media, TikTok, startups
- `minimalist-diagram` — Technical deep-dives, architecture
- `ink-sketch` — Hand-drawn ink doodle animation (Ink Theater)

Playbooks define typography, color palettes, motion styles, audio profiles, and quality rules. Validated against `schemas/styles/playbook.schema.json`.
