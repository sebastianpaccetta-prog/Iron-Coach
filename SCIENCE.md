# What the plan is based on

Every rule in `pipeline/plan.py` and `pipeline/training_load.py` maps to one of the
entries below. Only work published 2020 or later is used as justification; where a
rule is convention rather than evidence, it says so.

## Rules with direct evidence

| Rule | Where | Evidence |
|---|---|---|
| Long run capped at 110% of your longest run in the last 30 days | `MAX_LONG_RUN_SPIKE`, `_allocate` | Nielsen et al. 2025, *BJSM*. 5,205 runners, 588k sessions: a single run >10% longer than the longest in the prior 30 days raised overuse-injury rate 1.6x (small spike) to 2.3x (large spike). Weekly-total rules did not predict injury. |
| HRV compared against your own baseline band (0.5 x SD), 7-day rolling average | `recovery_status` | Düking et al. 2021, *J Sci Med Sport* meta-analysis (8 trials): HRV-guided training improved submaximal markers (g = 0.30) and produced fewer non-responders than fixed plans. Nuuttila et al. 2022 (*MSSE*) and Javaloyes et al. 2020 (*JSCR*) both used the rolling-average-vs-SWC method implemented here. |
| Taper = ~2 weeks, volume cut 41-60%, intensity and frequency kept | `PHASES`, `PHASE_TARGET_FRACTION` | Wang et al. 2023, *PLOS One* meta-analysis (14 studies): 41-60% volume reduction with intensity and frequency maintained gave significant time-trial gains; 8-14 day tapers were effective. |
| Pyramidal in base/build, polarised (adds Z5) in peak | `describe` sets by phase | Filipas et al. 2022, *Scand J Med Sci Sports*: 60 well-trained runners, 16 weeks; pyramidal-then-polarised beat either alone (+3% VO2peak, +1.5% 5 km TT). Rosenblat et al. 2024, *Sports Med* meta-analysis: polarised only clearly superior for VO2peak in short blocks in highly trained athletes; otherwise distributions perform similarly, so most volume stays Z1-Z2. |
| Heavy strength (>80% 1RM) + plyometrics | `describe` strength | Llanos-Lagos et al. 2024, *Sports Med* meta-analysis: heavy loading improved running economy most at race-relevant speeds; plyometrics at slower speeds; combined best at 10-14 km/h. |
| 90 g carbs/h target, train the gut to 90-120 g/h | `describe` long ride, race day | Podlogar & Wallis 2022, *Sports Med*: 90 g/h glucose:fructose is the well-supported ceiling for oxidation; 120 g/h is tolerable when trained (Viribay et al. 2020) but does not spare glycogen further. |

## Rules that are convention (kept, labelled honestly)

| Rule | Where | Status |
|---|---|---|
| <=10% weekly volume ramp | `MAX_WEEKLY_RAMP` | Not supported as an injury preventer (Impellizzeri et al. 2020, *IJSPP*, on ACWR; 2022 systematic review of 36 studies found no consistent link between weekly-volume change and injury). Kept as a conservative default; the session-spike cap above is the evidence-based guard. |
| CTL 42-day / ATL 7-day / TSB | `load_series` | The fitness-fatigue model is old but is still the basis of TrainingPeaks, Intervals.icu and current modelling papers. Treat TSB as a trend indicator, not a precise number. |
| TSS = h x IF^2 x 100 | `activity_tss` | Standard load estimate. Weakest for swimming and strength (hence `SPORT_TSS_SCALE`). HR-derived IF drifts with heat and fatigue. |
| Every 4th week a deload at 65% | `RECOVERY_EVERY_N_WEEKS` | Near-universal coaching practice; no trial isolates the exact ratio. |
| Peak week 11-14 h chosen from fitness | `peak_week_hours` | 11-14 h is the typical range for sub-5 age-groupers. The mapping from recent hours / CTL to a point in that range is a heuristic, not a finding. |
| Sport split by phase, session minimums, day template | `SPORT_SPLIT`, `WEEK_TEMPLATE` | Coaching judgment. Bike-heavy because the bike is ~52% of a 70.3 by time. |
| Goal-pace sanity check: run goal pace should be <=92% of threshold speed | `_goal_check` | Rule of thumb from 70.3 pacing data; a 70.3 run is typically held at ~88-92% of threshold. |

## Goal: sub-5 h 70.3

`GOAL_TIME_H = 5.0` in `config.py` drives every race-pace string. The reference split
(35 / 4 / 156 / 3 / 102 min) is scaled to the goal time; change the goal and the
paces move with it. Current implied targets:

* swim 1:51 / 100 m
* bike 21.5 mph
* run 7:47 / mi

Units are set by `UNITS` in `config.py` (`"imperial"` = min/mi, mph, miles; `"metric"` =
min/km, km/h, km). Swim pace is always per 100 m.

## Sources

* Nielsen RØ et al. (2025). How much running is too much? Identifying high-risk running sessions in a 5200-person cohort study. *Br J Sports Med*. https://pmc.ncbi.nlm.nih.gov/articles/PMC12421110/
* Düking P et al. (2021). Monitoring and adapting endurance training on the basis of heart rate variability monitored by wearable technologies: a systematic review with meta-analysis. *J Sci Med Sport* 24(11):1180-92. https://pubmed.ncbi.nlm.nih.gov/34489178/
* Manresa-Rocamora A et al. (2021). HRV-guided training for enhancing cardiac-vagal modulation, aerobic fitness, and endurance performance: a methodological systematic review with meta-analysis. *Int J Environ Res Public Health*. https://pubmed.ncbi.nlm.nih.gov/34639599/
* Wang Z et al. (2023). Effects of tapering on performance in endurance athletes: a systematic review and meta-analysis. *PLOS One* 18(5):e0282838. https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0282838
* Filipas L et al. (2022). Effects of 16 weeks of pyramidal and polarized training intensity distributions in well-trained endurance runners. *Scand J Med Sci Sports* 32(3):498-511. https://pmc.ncbi.nlm.nih.gov/articles/PMC9299127/
* Rosenblat MA et al. (2024). Comparison of polarized versus other types of endurance training intensity distribution on athletes' endurance performance: a systematic review with meta-analysis. *Sports Med*. https://link.springer.com/article/10.1007/s40279-024-02034-z
* Llanos-Lagos C et al. (2024). Effect of strength training programs in middle- and long-distance runners' economy at different running speeds: a systematic review with meta-analysis. *Sports Med* 54:895-932. https://pmc.ncbi.nlm.nih.gov/articles/PMC11052887/
* Podlogar T, Wallis GA (2022). New horizons in carbohydrate research and application for endurance athletes. *Sports Med* 52(Suppl 1):5-23. https://www.gssiweb.org/sports-science-exchange/article/dietary-carbohydrate-and-the-endurance-athlete-contemporary-perspectives
* Impellizzeri FM et al. (2020). Acute:chronic workload ratio: conceptual issues and fundamental pitfalls. *Int J Sports Physiol Perform* 15(6):907-13. https://pubmed.ncbi.nlm.nih.gov/32502973/
* Systematic review of running injuries and training parameters (2022, 36 studies). https://pmc.ncbi.nlm.nih.gov/articles/PMC9528699/
