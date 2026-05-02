# Block Report: sar_adc_top

## Status: PASS
Verified: 2026-05-03 01:32

## Verification Results
| Test | Result | Pass |
|------|--------|------|
| Analog input waveform captured | V(analog_in) | PASS |
| Internal SAR conversion nodes are present | V(dac_out) | PASS |
| Transient simulation produced enough samples | time length=3887 | PASS |

## Measurements
| Name | Value |
|------|-------|
| signal_count | 33 |
| time_points | 3887 |
| input_span_v | 0.07848814941164206 |
| input_mean_v | 1.2885320682818846 |
| output_span_v | 0.3021346708039474 |
| output_final_v | 1.2507 |
| tracked_signals | I(a$poly$e_dac), I(ae_b5), I(ae_b6), I(ae_b7), V(analog_in) |
