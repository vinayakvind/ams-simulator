# Block Report: sigma_delta_adc_top

## Status: PASS
Verified: 2026-05-02 19:45

## Verification Results
| Test | Result | Pass |
|------|--------|------|
| Analog input waveform captured | V(analog_in) | PASS |
| Modulator bitstream is present | V(bitstream) | PASS |
| Internal sigma-delta nodes are present | V(dec_filt) | PASS |
| Transient simulation produced enough samples | time length=103092 | PASS |

## Measurements
| Name | Value |
|------|-------|
| signal_count | 28 |
| time_points | 103092 |
| input_span_v | 0.5877852522924729 |
| input_mean_v | 1.5539081915241186 |
| output_span_v | 0.008907732826050951 |
| output_final_v | 1.658907732826142 |
| bitstream_mean_v | 1.662156270666165 |
| tracked_signals | I(a$poly$e_sum), I(ae_comp), I(ae_dac), V(analog_in), I(be_comp) |
