# Final Autopilot Model Artifacts

This update aligns the Autopilot CSVs, traces, learned state machines, PTA models, and RQ2 NuSMV artifacts with the final MELA/Baseline setup.

## MELA

- CSV abstractions are in `Data/Autopilot/Abstraction/MELA/{ascend,descend}`.
- Trace CSV/TXT files are in `Data/Autopilot/Trace/MELA/{ascend,descend}`.
- Learned state machines are in `Results/Autopilot/LearnedModel/MELA/{ascend,descend}/gsm_models`.
- PTA DOT models are in `Results/Autopilot/RQ2/{ascend,descend}/PTA/pta_models/MELA`.
- PTA NuSMV `.smv` files are in `Results/Autopilot/RQ2/{ascend,descend}/PTA/generated_models`.
- Raw NuSMV outputs and the provided PTA result workbooks are in `Results/Autopilot/RQ2/summary/pta_results`.
- The regenerated AG GSM-vs-PTA summary is in `Results/Autopilot/RQ2/summary/ag_not_target_gsm_pta_results.csv`; the full regenerated report is in `Results/Autopilot/RQ2/summaries/ag_not_target_property_check`.
- Final throttle merges the old low and med regions into `low`; the final throttle labels are `low` and `high`.
- The combined PitchWheel+Throttle case is made by putting the final separate PitchWheel and Throttle labels together. It does not use a separate combined decision tree.

## Baseline

- CSV abstractions are in `Data/Autopilot/Abstraction/Baseline/{ascend,descend}`.
- Trace CSV/TXT files are in `Data/Autopilot/Trace/Baseline/{ascend,descend}`.
- Learned state machines are in `Results/Autopilot/LearnedModel/Baseline/{ascend,descend}/gsm_models`.
- PitchWheel uses the manual baseline split: low <= -10, med > -10 and <= 10, high > 10.
- Throttle uses the requested binary split: low <= 0.5, high > 0.5.
- The combined PitchWheel+Throttle case is made by putting these separate PitchWheel and Throttle labels together. It does not use a separate combined decision tree.

## Counts

- `Results/Autopilot/LearnedModel/state_machine_counts_report.csv`
- `Results/Autopilot/LearnedModel/MELA/state_machine_counts_report.csv`
- `Results/Autopilot/LearnedModel/Baseline/state_machine_counts_report.csv`
- `Results/Autopilot/RQ2/summary/pta_counts_report.csv`
