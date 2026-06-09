# RQ2 AG Not-Target Report

RQ2 checks non-corrective inputs and requires that outputs do not improve.

Important correction: GSM results are computed from the reachable GSM SMV transition relation, and PTA results are computed from the reachable PTA DOT transition relation. This avoids the PTA bug where making `input_label` a free checker variable makes alphabet-only labels look reachable in EF checks.

Temporary checked NuSMV files are still written under `generated_checker_models` for audit, but the CSV result columns use parsed transition tables as the source of truth.

The CSV includes PTA DOT details for each row: matching transition count, source states, transition labels, next states, and next outputs.

CTL rules used:

`CTLSPEC AG((output = out_critical & input_label = INPUT) -> AX(!(output = out_caution)));`

`CTLSPEC AG((output = out_caution & input_label = INPUT) -> AX(!(output = out_nominal)));`

Vacuity check:

`CTLSPEC EF(output = source_output & input_label = INPUT);`

Final-result mapping: AG TRUE + EF TRUE = PASS; AG TRUE + EF FALSE = VACUOUS; AG FALSE = VIOLATION.

## Models Checked

- GSM Ascent: `Results/Autopilot/RQ2/ascend/generated_models/pitchwheel_throttle/pitchwheel_throttle_model.smv`
- GSM Descent: `Results/Autopilot/RQ2/descend/generated_models/pitchwheel_throttle/pitchwheel_throttle_model.smv`
- PTA Ascent: `Results/Autopilot/RQ2/ascend/PTA/generated_models/pitchwheel_throttle/pta_pitchwheel_throttle_model.smv`
- PTA Descent: `Results/Autopilot/RQ2/descend/PTA/generated_models/pitchwheel_throttle/pta_pitchwheel_throttle_model.smv`

## Summary

- Rows: 24
- GSM PASS: 9
- GSM VIOLATION: 8
- GSM VACUOUS: 7
- PTA PASS: 9
- PTA VIOLATION: 8
- PTA VACUOUS: 7
- Same final result: 24
- Different final result: 0

## Results

| Command | Rule | Input | GSM | PTA | Same |
|---|---|---|---|---|---|
| Ascent | CR_not_CA | `p_low_t_low` | PASS | PASS | YES |
| Ascent | CA_not_N | `p_low_t_low` | PASS | PASS | YES |
| Ascent | CR_not_CA | `p_low_t_high` | VACUOUS | VACUOUS | YES |
| Ascent | CA_not_N | `p_low_t_high` | VACUOUS | VACUOUS | YES |
| Ascent | CR_not_CA | `p_med_t_low` | VIOLATION | VIOLATION | YES |
| Ascent | CA_not_N | `p_med_t_low` | VIOLATION | VIOLATION | YES |
| Ascent | CR_not_CA | `p_med_t_high` | VACUOUS | VACUOUS | YES |
| Ascent | CA_not_N | `p_med_t_high` | VACUOUS | VACUOUS | YES |
| Ascent | CR_not_CA | `p_high_t_low` | VIOLATION | VIOLATION | YES |
| Ascent | CA_not_N | `p_high_t_low` | PASS | PASS | YES |
| Ascent | CR_not_CA | `p_high_t_high` | VIOLATION | VIOLATION | YES |
| Ascent | CA_not_N | `p_high_t_high` | VIOLATION | VIOLATION | YES |
| Descent | CR_not_CA | `p_low_t_low` | VIOLATION | VIOLATION | YES |
| Descent | CA_not_N | `p_low_t_low` | VIOLATION | VIOLATION | YES |
| Descent | CR_not_CA | `p_low_t_high` | VACUOUS | VACUOUS | YES |
| Descent | CA_not_N | `p_low_t_high` | VIOLATION | VIOLATION | YES |
| Descent | CR_not_CA | `p_med_t_low` | PASS | PASS | YES |
| Descent | CA_not_N | `p_med_t_low` | PASS | PASS | YES |
| Descent | CR_not_CA | `p_med_t_high` | VACUOUS | VACUOUS | YES |
| Descent | CA_not_N | `p_med_t_high` | PASS | PASS | YES |
| Descent | CR_not_CA | `p_high_t_low` | PASS | PASS | YES |
| Descent | CA_not_N | `p_high_t_low` | VACUOUS | VACUOUS | YES |
| Descent | CR_not_CA | `p_high_t_high` | PASS | PASS | YES |
| Descent | CA_not_N | `p_high_t_high` | PASS | PASS | YES |

## Skipped `.smv` Files

- `Results/Autopilot/RQ2/ascend/PTA/generated_models/pitchwheel/pta_pitchwheel_model.smv`: not Top-2 RQ2 model; missing p_high_t_high, p_high_t_low, p_low_t_high, p_low_t_low, p_med_t_high, p_med_t_low
- `Results/Autopilot/RQ2/ascend/PTA/generated_models/throttle/pta_throttle_model.smv`: not Top-2 RQ2 model; missing p_high_t_high, p_high_t_low, p_low_t_high, p_low_t_low, p_med_t_high, p_med_t_low
- `Results/Autopilot/RQ2/ascend/generated_models/pitchwheel/pitchwheel_model.smv`: not Top-2 RQ2 model; missing p_high_t_high, p_high_t_low, p_low_t_high, p_low_t_low, p_med_t_high, p_med_t_low
- `Results/Autopilot/RQ2/ascend/generated_models/throttle/throttle_model.smv`: not Top-2 RQ2 model; missing p_high_t_high, p_high_t_low, p_low_t_high, p_low_t_low, p_med_t_high, p_med_t_low
- `Results/Autopilot/RQ2/descend/PTA/generated_models/pitchwheel/pta_pitchwheel_model.smv`: not Top-2 RQ2 model; missing p_high_t_high, p_high_t_low, p_low_t_high, p_low_t_low, p_med_t_high, p_med_t_low
- `Results/Autopilot/RQ2/descend/PTA/generated_models/throttle/pta_throttle_model.smv`: not Top-2 RQ2 model; missing p_high_t_high, p_high_t_low, p_low_t_high, p_low_t_low, p_med_t_high, p_med_t_low
- `Results/Autopilot/RQ2/descend/generated_models/pitchwheel/pitchwheel_model.smv`: not Top-2 RQ2 model; missing p_high_t_high, p_high_t_low, p_low_t_high, p_low_t_low, p_med_t_high, p_med_t_low
- `Results/Autopilot/RQ2/descend/generated_models/throttle/throttle_model.smv`: not Top-2 RQ2 model; missing p_high_t_high, p_high_t_low, p_low_t_high, p_low_t_low, p_med_t_high, p_med_t_low
