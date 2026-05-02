# LIN ASIC Regression Report

- Generated: 2026-05-02T19:55:14.384038
- Standard Target: ISO 17987 / LIN 2.2A
- Overall: PASS

## Summary

- Total tests: 10
- Passed: 10
- Failed: 0
- Functional coverage: 100.0%
- Standards-linked coverage: 50.0%

## Test Results

| Case ID | Block | Status | Details |
|---------|-------|--------|---------|
| ANA-BGR-STARTUP | bandgap | PASS | VREF startup and settling when VDD powers on from 0 V. Verifies nominal output (1.2 V ± 5 %) Mean=1.200V. |
| ANA-LDO-3V3 | ldo_analog | PASS | Output regulation when 12 V supply powers on. Verifies VOUT = 3.3 V ± 5 % Mean=3.300V. |
| ANA-LDO-1V8 | ldo_digital | PASS | Output regulation when 3.3 V supply powers on. Verifies VOUT = 1.8 V ± 5 % Mean=1.800V. |
| ANA-LDO-5V0 | ldo_lin | PASS | Output regulation for LIN bus driver power-up. Verifies VOUT = 5.0 V ± 5 % Mean=5.000V. |
| ANA-LIN-BUS-SWING | lin_transceiver | PASS | Bus voltage swing between dominant and recessive states. Verifies V_bus_high > 10 V and V_bus_low < 2 V High=11.486V Low=1.091V. |
| DIG-SPI-DECODE | spi_controller | PASS | SPI slave transaction decode from SCLK/MOSI/CS_N into register address/control handoff |
| DIG-REGFILE-CONTROL | register_file | PASS | Reset defaults, CTRL register write, and baud-divisor fanout were exercised (mask=0x0F, baud_div=0x0234). |
| DIG-LIN-CTRL | lin_controller | PASS | Behavioral RTL reset, state-machine bring-up, and LIN master break/sync control-path readiness |
| DIG-CTRL-SEQUENCE | control_logic | PASS | Power sequence advanced through BGR, analog LDO, digital LDO, LIN enable, then de-asserted LIN in sleep mode. |
| TOP-MS-BRIDGE | lin_mixed_signal_interface | PASS | Digital TXD logic level drives the analog LIN bus, and the analog bus is thresholded back into RXD logic |

Regression log: C:\Users\vinay\My Simulator\reports\lin_asic_regression_latest.log

## Test Plan

See C:\Users\vinay\My Simulator\designs\lin_asic\LIN_ASIC_TESTPLAN.md for the detailed ASIC test plan.