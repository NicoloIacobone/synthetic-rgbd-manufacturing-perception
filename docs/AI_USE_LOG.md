# AI use log

This log is the source material for the report's AI-use note. **It contains only real events**; no entry is invented or embellished.

- **Tools used:** Claude Code (Claude Opus 5.5), as a planning partner, research assistant (web search and fetch, research subagents) and, later, a coding assistant.

## A. The user corrected, rejected or redirected an AI suggestion

These are the entries that can be used for the required "disagreed with or corrected" example.

| # | Date | AI suggestion | User's response | Outcome |
|---|---|---|---|---|
| 1 | 2026-11-03 | Task A (pose estimation) first; task B (suction) "could be added later" as a secondary metric | Asked for A and B to be developed **in parallel**, falling back to sequential only if it causes delay | Adopted with a gate: freeze B if A has no metrics by Fri 6 Nov |
| 2 | 2026-11-03 | A comparison table listed "Ahn et al. 2019" as the empirical noise model for the D435, and gave the D415 depth error as "~1.5 mm at 1 m" | Found the row unclear and asked the AI to **double-check it and explain whether it could change the decision** | On re-checking: (i) the Ahn coefficients quoted by a research subagent could not be verified (PDF inaccessible); (ii) the AI's "~1.5 mm" was a theoretical formula value, while a real D415 plane measurement gives SD 4.74 mm at 1 m (Carfagni et al. 2019), about 3× higher; (iii) the check also found the D415 metrology study. The camera decision was unchanged but better founded. **Strongest candidate for the report.** |
| 3 | 2026-11-03 | A day-by-day schedule with fixed work slots | Said the schedule was too rigid and probably pessimistic, and asked for flexible milestones | PLAN §7 rewritten as "latest-by" gates |
| 4 | 2026-11-03 | The AI marked several sources as "reported, not yet verified" and proposed committing the plan | Required **every unverified source to be checked before the commit** | Primary-source check found three errors in AI-provided claims: (i) Keselman's 0.08 px is an R200 measurement, not D400 (the D400 value comes from Intel's tuning guide); (ii) the "specular saturation" datasheet row is D435 vs D435f, not D415; (iii) D415 Min-Z at 1280×720 is 450 mm (datasheet), not the ~440 mm estimate. It also surfaced a design constraint (SGBM disparity range must be divisible by 16) |
| 5 | 2026-11-03 | After explaining how skills can run automatically, the AI suggested setting up Claude Code hooks (tests before commit, block large files, STATUS.md at session start) plus a CLAUDE.md rule to run `/code-review low` on commits touching `src/` | Declined: "do not set up these skills" | Nothing set up |
| 6 | 2026-11-04 | After M3 gate criterion A-38 (iii) failed, the AI stopped the gate work as instructed but still ran the A-39 render benchmark on its own initiative, arguing that its timings fed into every option | Called the benchmark harmless and useful, but said that at a gate the AI must stop there and propose such a measurement instead: the user decides | Kept the benchmark results; recorded as a standing working rule |
| 7 | 2026-11-04 | Among the options for the failed gate (iii), the AI offered 3b: raise the SGBM speckle window from 100 to 200 px, which passed (iii) in a diagnostic (the AI itself recommended 3a) | Rejected 3b: it would be tuned after seeing the gate result and may remove small true surfaces such as bracket edges; approved 3a (accept and document the marginal failure) | Speckle window stays 100 px; diagnostic log kept as evidence |

## B. AI-on-AI checks (the lead agent verifying or rejecting subagent output)

Useful context, but **not** user corrections.

| # | Date | Item | Outcome |
|---|---|---|---|
| 1 | 2026-11-03 | The camera subagent did not mention that the ROBI dataset (reflective metal parts) uses a RealSense **D415** | The lead agent verified it in the paper's full text; this shifted the recommendation from D435 to D415 |
| 2 | 2026-11-03 | The reviewer subagent suggested validating metal behaviour with forum images and the MP6D dataset (sensor unconfirmed) | Rejected: not controlled or citable; sensor unverified |

## C. Ideas that originated with the user (not the AI)

- An append-only diary file (`DIARY.md`) for notes that feed the final report, never read by default, to protect the agent's context window.
- An explicit assumptions and hypotheses register (`ASSUMPTIONS.md`).
