# Report plan

Page budget and reflection outline for the PDF report (≤ 8 pages including reflection and AI note, A-01). Moved out of PLAN.md §10–11 on 2026-11-03.

**When to read:** when choosing which results or figures to produce, and during report writing (M6).

## 1. Report outline (≤ 8 pages total)

| § | Content | Pages |
|---|---|---|
| 1 | Problem, scope, non-goals | 0.5 |
| 2 | Reference camera: why the D415 | 0.5 |
| 3 | Synthetic data pipeline | 1.0 |
| 4 | Camera model: active stereo simulation, included/excluded table, anchor (a) | 1.5 |
| 5 | Experiment design and pre-specified endpoint | 0.75 |
| 6 | Results, incl. what did not work | 1.5 |
| 7 | Limitations | 0.5 |
| 8 | Synthetic-to-real reflection (≤ 1 page) | 1.0 |
| 9 | AI-use note | 0.25 |
| — | References | ~0.5 |

## 2. Reflection outline (tentative until results)

**Riskiest assumption candidates**
- **(a) Preferred:** the simulated sensor reproduces how the real sensor errs on reflective metal. Links to the C3 vs C4 result; ROBI suggests the real D415 smooths metal rather than leaving holes [S-05].
- **(b)** Randomised appearance in simulation covers real factory surfaces.
- **(c)** Pose error in simulation predicts real pick or assembly success.

**Six-month plan for (a)**
1. **Months 1–2:** collect a small real calibration set with the target camera on real parts; ground-truth depth from spray-coated scanning (ROBI protocol).
2. **Months 2–3:** measure the simulation-to-reality gap effect by effect.
3. **Months 3–4:** fit the sensor-model parameters or learn a residual correction; randomise what remains unmodelled.
4. **Months 5–6:** closed-loop pick and assembly validation, with success criteria and go/no-go thresholds fixed in advance.
