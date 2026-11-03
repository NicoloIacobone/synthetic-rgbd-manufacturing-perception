# Project instructions for AI agents

ETH Zurich PhD application assignment: synthetic RGB-D of aluminium profiles and brackets with a RealSense D415 camera model, and its effect on downstream pose estimation and suction grasping. Deadline Sun 2026-11-08 23:59 CET. The deliverable is a PDF report (**≤ 8 pages including reflection and AI note**) plus runnable code.

## Context files

| File | When to read | Notes |
|---|---|---|
| `docs/STATUS.md` | **First**, at the start of every task | Current state and next steps. Update at the end of every task |
| `task_description.md` | Start of every task | Authoritative requirements. Never edit |
| `docs/PLAN.md` | Start of every task | Decisions, protocol, milestones, risks |
| `docs/ASSUMPTIONS.md` | Start of every task | Assumptions and hypotheses register; add or update rows |
| `docs/SOURCES.md` | When citing, verifying or adding a source, and during report writing | Source list with verification status |
| `docs/REPORT_PLAN.md` | When choosing results or figures to produce, and during report writing | Page budget per section; reflection outline |
| `docs/AI_USE_LOG.md` | Only when adding an entry | Append with the shell |
| `docs/DIARY.md` | **Never**, unless the user asks or during report writing | Append-only, see below |

## Working rules

- **The user decides.** Present options with consequences; do not treat agent or subagent output as approved. Do not re-open decisions recorded in PLAN.md §2 unless new evidence warrants it, and then say so.
- **Protocol freeze:** PLAN.md §5 and `configs/default.yaml` are frozen at git tag `protocol-v1`. Any change is a deviation: get the user's approval, then log it with date and reason in PLAN.md §5.12.
- **Citations:** link every technical claim to its source, and check the claim against the primary source before it enters the report. Keep the status in `docs/SOURCES.md` up to date (✅ verified / 🔶 unverified / ⚠️ partial). Distinguish facts, inferences and assumptions.
- **Assumptions:** any new modelling, scoping or evaluation choice gets a row in `docs/ASSUMPTIONS.md`. Nothing stays implicit.
- **Status:** at the end of every task, update `docs/STATUS.md` (overwrite outdated content; keep it short).
- **Diary:** after each completed task or subtask, and whenever something fails or surprises, append a dated entry to `docs/DIARY.md` using `cat >> docs/DIARY.md <<'EOF'`. Do not read the file first. Record numbers with units, seeds and commit hashes.
- **AI-use log:** when the user corrects, rejects or redirects an AI suggestion, append a real, factual entry to `docs/AI_USE_LOG.md` section A. Never invent entries.
- **8-page budget:** prefer results and figures that map to a report section (`docs/REPORT_PLAN.md`).
- **Context hygiene:** run long jobs (renders) in the background with logs written to a file, and read only `tail`/`grep` excerpts. Downscale images before viewing them.

## Git

- **Commit when a task or subtask is complete and verified**, not mid-way. One coherent change per commit.
- **Commit messages:** imperative subject ≤ 72 chars, with a type prefix (`docs:`, `feat:`, `fix:`, `exp:`, `chore:`, `test:`), then a body explaining what and why, and which milestone, decision or assumption is affected.
- **Never commit** generated datasets, renders, the downloaded Blender, virtual environments, or `.DS_Store`; keep them in `.gitignore`. Small sample outputs for the README are fine if deliberately chosen.
- **No remote creation, no push, no history rewriting** unless the user explicitly asks. Never move or delete the `protocol-v1` tag.

## Environment

- Apple M2, 8 GB RAM, macOS 27.2. Render one process at a time.
- BlenderProc runs scripts inside Blender's bundled Python. Analysis code, including IR noise and SGBM stereo matching (D13), runs in the **separate** env `.venv` (Python 3.11, pins in `requirements.txt`, lock in `requirements.lock.txt`); the system Python is 3.14 and is not used.
- Package code lives in `src/synthrgbd/`, protocol parameters in `configs/default.yaml`, tests in `tests/` (`.venv/bin/python -m pytest`). Run the tests before every commit that touches `src/`.
- Seeds follow PLAN §5.10 (`src/synthrgbd/seeds.py`) and are logged for every generated dataset and experiment run.
