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

**Figures ready, all regenerable with `scripts/make_figures.sh`:** `results/figures/results.png` (§6), `robi.png` (§7, §8), `examples.png` (§3), `mechanism.png` (§6, §7). Numbers: `results/hfov71/`, with the 65° run in `results/archive_hfov65/`. Under "what did not work" (§6): the Min-Z transition at 392 mm against the datasheet's 450 mm (A-67), and the matcher filling unlit strips with depth.

## 2. Reflection outline (tentative until results)

**Riskiest assumption candidates**
- **(a) Preferred:** the simulated sensor reproduces how the real sensor errs on reflective metal. Links to the C3 vs C4 result. Own ROBI Zigzag measure (`data/m5/robi/zigzag.json`, A-65): the real D415 leaves 21% of part pixels invalid against 2.3% in C3 at 71°, while its disparity errors are of similar size (p5 −2.07 px against −2.24 px), at another range; the same parts read 21 DN against 5 DN, with local contrast 4.6 against 22.5 DN; [S-05] says only "loss of geometric details". One test with ambient light matches the mean but not the local contrast (A-70).
- **(b)** Randomised appearance in simulation covers real factory surfaces.
- **(c)** Pose error in simulation predicts real pick or assembly success.

**Six-month plan for (a)**
1. **Months 1–2:** collect a small real calibration set with the target camera on real parts; ground-truth depth from spray-coated scanning (ROBI protocol).
2. **Months 2–3:** measure the simulation-to-reality gap effect by effect.
3. **Months 3–4:** fit the sensor-model parameters or learn a residual correction; randomise what remains unmodelled.
4. **Months 5–6:** closed-loop pick and assembly validation, with success criteria and go/no-go thresholds fixed in advance.
