# Block Report: sigma_delta_adc_top

## Status: PASS
Verified: 2026-04-30 00:50

## Verification Results
| Test | Result | Pass |
|------|--------|------|
| Analog input waveform captured | V(analog_in) | PASS |
| Modulator bitstream is present | V(bitstream) | PASS |
| Internal sigma-delta nodes are present | V(dec_filt) | PASS |
| Transient simulation produced enough samples | time length=157955 | PASS |

## Measurements
| Name | Value |
|------|-------|
| signal_count | 28 |
| time_points | 157955 |
| input_span_v | 1.999999999973439 |
| input_mean_v | 1.2607590966015434 |
| output_span_v | 0.06835870378670283 |
| output_final_v | 1.631980868244567 |
| bitstream_mean_v | 1.6504303636181155 |
| tracked_signals | I(a$poly$e_sum), I(ae_comp), I(ae_dac), V(analog_in), I(be_comp) |
