# LIN ASIC Complete Test Plan

## Scope

This plan covers the mixed-signal LIN ASIC implementation in this repository:
- Analog blocks: bandgap, LDO analog, LDO digital, LDO LIN
- Mixed-signal block: LIN transceiver
- Digital blocks: SPI controller, register file, LIN controller, control logic
- Top-level integration: digital-to-analog bridge, power-up sequencing, regression flow, API observability

## Standards And References

- Primary protocol target: ISO 17987 / LIN 2.2A
- LIN bus expectations used in this project:
  - Recessive bus state above 10V
  - Dominant bus state below 2V
  - Break field: 13 or more dominant bits plus delimiter
  - Sync byte: 0x55
  - PID parity: P0 = ID0 ^ ID1 ^ ID2 ^ ID4, P1 = ~(ID1 ^ ID3 ^ ID4 ^ ID5)
- Internal power-tree targets from the project architecture:
  - Bandgap: 1.2V reference, 1.14V to 1.26V acceptable band
  - LDO analog: 3.3V rail target
  - LDO digital: 1.8V rail target
  - LDO LIN: 5.0V rail target

## Verification Objectives

### Analog Objectives

| Case ID | Block | Objective | Pass Criteria |
|---------|-------|-----------|---------------|
| ANA-BGR-STARTUP | Bandgap | Verify startup and steady-state reference | 1.14V <= VREF <= 1.26V |
| ANA-LDO-3V3 | LDO Analog | Verify analog supply regulation | 3.1V <= VOUT <= 3.5V |
| ANA-LDO-1V8 | LDO Digital | Verify digital core regulation | 1.7V <= VOUT <= 1.9V |
| ANA-LDO-5V0 | LDO LIN | Verify LIN transceiver rail regulation | 4.75V <= VOUT <= 5.25V |
| ANA-LIN-BUS-SWING | LIN Transceiver | Verify dominant/recessive swing | VBUS_HIGH >= 10V and VBUS_LOW <= 2V |

### Digital Objectives

| Case ID | Block | Objective | Pass Criteria |
|---------|-------|-----------|---------------|
| DIG-SPI-DECODE | SPI Controller | Verify SPI framing and register decode | Address/data decode matches RTL expectations |
| DIG-REGFILE-CONTROL | Register File | Verify reset defaults, write path, decode outputs | Default control mask valid, writes update outputs, baud_div updates |
| DIG-LIN-CTRL | LIN Controller | Verify reset, state reachability, master/slave readiness | Reset settles cleanly, key outputs assert expected values |
| DIG-CTRL-SEQUENCE | Control Logic | Verify POR and enable sequencing | BGR -> ANA -> DIG -> LIN order achieved, sleep disables LIN |

### Top-Level Objectives

| Case ID | Block | Objective | Pass Criteria |
|---------|-------|-----------|---------------|
| TOP-MS-BRIDGE | LIN Mixed-Signal Interface | Verify TXD -> bus -> RXD bridge | Bus high/low and logic thresholds satisfy mixed-signal checks |

## Functional Coverage Plan

### Coverage Groups

1. Power-up coverage
   - Bandgap starts before any LDO output is considered valid
   - LDO analog, digital, and LIN rails all reach their target windows
   - POR de-asserts only after sequence completion

2. LIN protocol coverage
   - Break detection path exercised
   - Sync byte path exercised
   - PID parity logic path exercised
   - Master-mode ready path exercised
   - Digital TXD to analog bus and analog bus to RXD reconstruction exercised

3. Register/control coverage
   - Register file reset defaults exercised
   - Control register write and decode exercised
   - Baud divider write and fanout exercised
   - IRQ mask and W1C flag handling visible in source/test review

4. Debug and observability coverage
   - Terminal command execution visible in GUI
   - API session monitor visible in GUI
   - Test tracker shows test case status and regression summary
   - Digital descend opens source artifacts directly

## Test Execution Modes

### Terminal-Driven Regression

Primary command:

```powershell
python scripts/run_lin_asic_regression.py \
  --json reports/lin_asic_regression_latest.json \
  --markdown reports/lin_asic_regression_latest.md
```

### GUI-Driven Regression

Use the Verification/Test Tracker window:
- Run ASIC Regression
- Refresh Results
- Open Test Plan
- Focus Terminal
- Show API Monitor

### API-Driven Control

The GUI and terminal are intended to be controllable through API endpoints:
- Terminal status and output
- Terminal command execution and stop
- Regression launch and regression status
- Test-case catalog retrieval
- Test-plan retrieval

## Required Artifacts

| Artifact | Path |
|----------|------|
| Regression JSON | reports/lin_asic_regression_latest.json |
| Regression Markdown | reports/lin_asic_regression_latest.md |
| Test plan | designs/lin_asic/LIN_ASIC_TESTPLAN.md |
| SPI RTL | designs/lin_asic/rtl/spi_slave.v |
| LIN controller RTL | designs/lin_asic/rtl/lin_controller.v |
| Register file RTL | designs/lin_asic/rtl/register_file.sv |
| Control logic RTL | designs/lin_asic/rtl/control_logic.sv |

## Debug Workflow

1. Descend from the top-level schematic into a digital block.
2. Confirm the mapped RTL opens in a separate source window.
3. Launch regression from the terminal or the tracker window.
4. Observe pass/fail in the tracker window.
5. If a case fails, inspect the terminal output, open the source window, and use the API error monitor for correction attempts.

## Signoff Criteria

1. All regression cases pass.
2. Mixed-signal bridge passes with LIN bus voltage margins.
3. Analog rails remain within their target windows.
4. Digital source files exist and are reachable from GUI descend actions.
5. Terminal/API control surfaces report consistent status.
6. Test tracker reflects the latest regression report with no stale failures.