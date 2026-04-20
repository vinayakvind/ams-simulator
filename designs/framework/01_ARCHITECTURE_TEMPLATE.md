# 01 - Architecture Template

## How to Define a Chip Architecture

### Step 1: Create Architecture Spec (YAML)

Every design starts with an `architecture.yaml` file:

```yaml
chip:
  name: "MY_ASIC"
  technology: "generic180"     # generic180 | generic130 | generic65 | bcd180
  supply:
    vbat: 12.0                 # Battery/main supply
    vdd_io: 3.3                # I/O supply
    vdd_core: 1.8              # Digital core supply
  
blocks:
  - name: bandgap
    type: analog
    generator: bandgap_ref     # From BlockBuilder registry
    params:
      supply_voltage: 3.3
    ports: [VDD, VREF, GND, EN]
    
  - name: ldo_analog
    type: analog
    generator: ldo_analog
    params:
      io_voltage: 12.0
      supply_voltage: 3.3
    ports: [VIN, VOUT, GND, VREF, EN]

  - name: spi_slave
    type: digital
    source: rtl/spi_slave.v
    ports: [CLK, MOSI, MISO, CS_N, SCLK]

connectivity:
  - from: bandgap.VREF
    to: [ldo_analog.VREF, ldo_digital.VREF]
    
  - from: ldo_analog.VOUT
    to: [ldo_digital.VIN, lin_transceiver.VDD_IO]

pad_ring:
  - {name: VBAT, type: power, voltage: 12.0}
  - {name: GND, type: ground}
  - {name: LIN, type: io, standard: "LIN2.2A"}
  - {name: SPI_CLK, type: input}
  - {name: SPI_MOSI, type: input}
  - {name: SPI_MISO, type: output}
  - {name: SPI_CS_N, type: input}
```

### Step 2: Block Inventory

List every block with its type and critical specs:

| Block | Type | Key Spec | Generator |
|-------|------|----------|-----------|
| Bandgap Reference | Analog | VREF = 1.2V ± 2% | `bandgap_ref` |
| LDO Analog 3.3V | Analog | VOUT = 3.3V, Iload = 50mA | `ldo_analog` |
| LDO Digital 1.8V | Analog | VOUT = 1.8V, Iload = 30mA | `ldo_digital` |
| LDO LIN 5V | Analog | VOUT = 5.0V from VBAT | `ldo_lin` |
| LIN Transceiver | Mixed | ISO 17987, 20kbps | `lin_transceiver` |
| SPI Controller | Digital | 4-wire, 8-bit | `spi_controller` |
| Register File | Digital | 27 registers | `register_file` |

### Step 3: Power Architecture

```
VBAT (8-18V) ──┬── LDO_LIN ──── VDD_LIN (5V) ── LIN Transceiver
               │
               └── LDO_ANA ──┬── VDD_IO (3.3V) ── I/O Pads, Bandgap
                              │
                              └── LDO_DIG ── VDD_CORE (1.8V) ── Digital Logic
```

### Step 4: Generate Design Directory

```bash
python designs/framework/scripts/create_design.py \
    --name my_asic \
    --arch path/to/architecture.yaml
```

This creates the full directory tree with all block folders, specs, and testbenches.
