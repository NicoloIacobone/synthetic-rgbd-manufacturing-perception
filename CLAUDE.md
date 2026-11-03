# Project instructions for AI agents

ETH Zurich PhD application assignment: synthetic RGB-D of aluminium profiles and brackets with a RealSense D415 camera model, and its effect on downstream pose estimation and suction grasping. Deadline Sun 2026-11-08 23:59 CET. The deliverable is a PDF report (**≤ 8 pages including reflection and AI note**) plus runnable code.

## Context files

| File | When to read | Notes |
|---|---|---|
| `task_description.md` | Start of every task | Authoritative requirements. Never edit |
| `docs/PLAN.md` | Start of every task | Decisions, protocol, milestones, sources |
| `docs/ASSUMPTIONS.md` | Start of every task | Assumptions and hypotheses register; add or update rows |
| `docs/AI_USE_LOG.md` | Only when adding an entry | Append with the shell |
| `docs/DIARY.md` | **Never**, unless the user asks or during report writing | Append-only, see below |

## Working rules

- **The user decides.** Present options with consequences; do not treat agent or subagent output as approved. Do not re-open decisions recorded in PLAN.md §2 unless new evidence warrants it, and then say so.
- **Citations:** link every technical claim to its source, and check the claim against the primary source before it enters the report. Keep the status in PLAN.md §9 up to date (✅ verified / 🔶 unverified / ⚠️ partial). Distinguish facts, inferences and assumptions.
- **Assumptions:** any new modelling, scoping or evaluation choice gets a row in `docs/ASSUMPTIONS.md`. Nothing stays implicit.
- **Diary:** after each completed task or subtask, and whenever something fails or surprises, append a dated entry to `docs/DIARY.md` using `cat >> docs/DIARY.md <<'EOF'`. Do not read the file first. Record numbers with units, seeds and commit hashes.
- **AI-use log:** when the user corrects, rejects or redirects an AI suggestion, append a real, factual entry to `docs/AI_USE_LOG.md` section A. Never invent entries.
- **8-page budget:** prefer results and figures that map to a report section (PLAN.md §10).

## Git

- **Commit when a task or subtask is complete and verified**, not mid-way. One coherent change per commit.
- **Commit messages:** imperative subject ≤ 72 chars, with a type prefix (`docs:`, `feat:`, `fix:`, `exp:`, `chore:`), then a body explaining what and why, and which milestone, decision or assumption is affected.
- **Never commit** generated datasets, renders, the downloaded Blender, virtual environments, or `.DS_Store`; keep them in `.gitignore`. Small sample outputs for the README are fine if deliberately chosen.
- **No remote creation, no push, no history rewriting** unless the user explicitly asks.

## Environment

- Apple M2, 8 GB RAM, macOS. Render one process at a time.
- BlenderProc runs scripts inside Blender's bundled Python. Analysis code (Open3D, OpenCV, numpy) runs in a **separate** pinned Python 3.11/3.12 env (the system Python is 3.14).
- Seeds are fixed and logged for every generated dataset and experiment run.
