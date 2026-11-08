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
| 8 | 2026-11-05 | After the failed §5.11 gate, the AI proposed testing H0, H1, H3 and the damped solver on C1 at zero offset, plus the conditioning of the normal matrix of failing vs passing instances | Accepted the direction but added conditions: candidate list and selection rule written and committed **before** any run; H2 run again to check determinism and thread count; the 33 small drifts split into two groups; conditioning judged not sufficient, so also explain why fitness falls below 1 on ideal depth and check whether the visibility filters remove surface the camera sees; threshold not to be touched | Rule pre-declared (A-62, ledger) before any candidate ran. The AI's conditioning inference did not hold for the 43 failures (fewer failures at high conditioning number). The check the user asked for led to the cause: a bug in the AI-written ray-cast cache gave profiles the mesh of another length, removing end faces the camera sees |
| 9 | 2026-11-05 | After the second §5.11 round the AI stopped with the dev selection as a proposal, plus a list of unexplained items | Approved it and redirected: close M5 and write down anything wrong or uncertain instead of stopping for it, because the work was turning into a loop and a completed milestone was needed before running a review agent | `docs/M5_OPEN_ITEMS.md`; M5 closed on 2026-11-05 |
| 10 | 2026-11-05 | The AI was waiting for a background job's notification; the job had died when the session ended. This happened twice: the dev selection, then the M5 run | Asked twice whether the AI was still waiting on something, which is how it came out | The M5 driver was relaunched detached from the session and resumed from its finished files |
| 11 | 2026-11-06 | After reading the datasheet the AI found that fx 1004.6 px comes from the 65° depth FOV while the imager is 71° ± 1°, and recommended disclosing this as a limitation without re-rendering, because the estimated effect is small and the value is frozen | Rejected: change the focal length and re-run the render and the experiment | Recorded in STATUS; carried out as a logged protocol deviation |
| 12 | 2026-11-06 | The AI recommended moving the code freeze from Sat 20:00 to Sun 12:00, because the remaining work did not fit 6 h/day | Rejected: keep the date and ignore the 6 h/day limit, since agents can run 10–12 h/day and overnight, with a final sprint on Sunday if needed | Budget note dropped from the planning; the freeze itself is run only when the user says so |
| 13 | 2026-11-07 | In the full review the AI recommended stating the untested dot density only as a limitation, because a test now would be one more measurement made after seeing the results | Redirected: state it as a limitation for now and also run a descriptive test with 10 000 dots on seeds 0–9, then decide from the result | Test run with the reading fixed in advance (A-74); the result goes back to the user |
| 14 | 2026-11-07 | The AI presented the quick-run risk on other platforms as a choice between a Linux test and a README line | Challenged the framing: why does Linux matter, and is there not a container or similar that always works? | The AI answered that a container fixes the system and the libraries but not the CPU, so the real weak point is the pixel-exact pass rule; the choice is with the user |
| 15 | 2026-11-08 | The report draft, written by the AI from sources it had marked verified, described Zhang et al.'s 3D-printed objects as "replicas" of their real objects, and cited Intel's tuning guide without noting that it computes the focal length from 65° | Downloaded every cited PDF to `docs/references/` and asked for a full-text double check of the report and the repo docs, then for the fixes that touch citations only | The two object sets are separate (9 printed, 8 real-life); wording corrected in Related work and Reflection, the 65° use of Intel's guides and ROBI's 0.8 mm camera-pose residual added, references [3], [10], [22] completed. One downloaded file (the BRDF paper) was a different paper. No number or result changed |

## B. AI-on-AI checks (the lead agent verifying or rejecting subagent output)

Useful context, but **not** user corrections.

| # | Date | Item | Outcome |
|---|---|---|---|
| 1 | 2026-11-03 | The camera subagent did not mention that the ROBI dataset (reflective metal parts) uses a RealSense **D415** | The lead agent verified it in the paper's full text; this shifted the recommendation from D435 to D415 |
| 2 | 2026-11-03 | The reviewer subagent suggested validating metal behaviour with forum images and the MP6D dataset (sensor unconfirmed) | Rejected: not controlled or citable; sensor unverified |

## C. Ideas that originated with the user (not the AI)

- An append-only diary file (`DIARY.md`) for notes that feed the final report, never read by default, to protect the agent's context window.
- An explicit assumptions and hypotheses register (`ASSUMPTIONS.md`).

### Added 2026-11-04 (pre-M4 design review)

| # | Date | AI suggestion | User's response | Outcome |
|---|---|---|---|---|
| 8 | 2026-11-04 | Fixed-sequence testing in the frozen §5.6 order: C1 vs C3 → C3 vs C4 → C2b vs C3 (C2b vs C3 last, as an add-on to H-1) | Reordered to C1 vs C3 → **C2b vs C3** → C3 vs C4: C2b vs C3 answers the task's question directly, and C3 vs C4 depends most on the unsourced metal roughness, so it goes last | Adopted in the pending §5.12 row |
| 9 | 2026-11-04 | M4 order: camera model first (albedo matching, exposure, IR noise, roughness), then the ICP/suction harness, then the pilot | Moved the harness to the front: it is the critical path and does not depend on the camera model; tuning still waits until all conditions exist on dev | M4 step 1 = harness + C1 sanity check |
| 10 | 2026-11-04 | In status reports the AI twice stated the date and time as "Thursday 00:30" (and dated a diary entry 2026-11-05) | Corrected it twice: it was Wednesday ~16:20–16:30 CET, about a day ahead of plan | Diary entry corrected; the schedule reasoning uses the real date |

AI-on-AI (section B), same review: the adversarial subagent reversed two of the lead agent's proposals. (i) The exposure gain was to be computed on the matte (C4) image; it was changed to the metal (C3) image, so the headline camera's auto exposure reacts to metal. (ii) Holm correction over three tests was replaced by fixed-sequence testing, so the first test keeps α = 0.05. It also corrected an over-generalisation from a single tilted view (metal "bias" is mostly a heavy tail).

### Added 2026-11-04 (evening)

| # | Date | AI suggestion | User's response | Outcome |
|---|---|---|---|---|
| 11 | 2026-11-04 | Agent status reports wrote bare project codes (D1, R5, §5.8) | Said the codes were confusing and that many prompts in one day had cost them control of the project; asked for a personal from-zero guide and a code dictionary | `docs/GLOSSARY.md` added; CLAUDE.md now requires each code to be written with its meaning |

AI-on-AI (section B), same evening: a second agent re-counted the M5 stop report from the result file. All its numbers held, but it had pooled two kinds of small ICP drift under one median and had not followed up low fitness on ideal depth; its remark that short profiles failing most does not fit a lever-arm effect is only half right (DIARY, 2026-11-04 ~21:15).

### Added 2026-11-06 (independent review of M5)

| # | Date | AI suggestion | User's response | Outcome |
|---|---|---|---|---|
| 12 | 2026-11-06 | The review agent recommended disclosing open item 18 (the §5.8 check had left the left-right filter on) rather than re-running it, arguing from a bound that a re-run could not flip the ranking | Accepted the agent's other four recommendations but rejected this one: try the re-run first, and disclose only if it still does not work | Re-run with the check really off (A-63): it works and the ranking does not flip, as the bound predicted. §5.8 is now done as the protocol defines it, instead of carrying a disclosed gap |

AI-on-AI (section B), same review: the agent suspected that the IR noise, about three times what real ROBI images allow, might be setting the metal result, and proposed a measurement. It did not hold: at about a third of the noise metal recall stayed 0.143 (A-64).
