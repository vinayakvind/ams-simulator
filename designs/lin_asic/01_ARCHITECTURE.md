# LIN ASIC - Architecture Definition

## Chip: LIN_ASIC
## Technology: BCD 180nm (generic180 for simulation)
## Application: ISO 17987 LIN Bus Slave Node

## Block Diagram

```
                    VBAT (8-18V)
                        |
                   +---------+
                   | LDO_LIN |---> VDD_LIN (5V) ---> LIN Transceiver
                   +---------+
                        |
                   +---------+
                   | LDO_ANA |---> VDD_IO (3.3V) ---> I/O, Bandgap
                   +---------+
                        |
                   +---------+
                   | LDO_DIG |---> VDD_CORE (1.8V) ---> Digital Logic
                   +---------+
                        |
           +------------+------------+
           |                         |
      +---------+            +-------------+
      | Bandgap |            | LIN         |
      | 1.2V    |            | Transceiver |<===> LIN Bus
      +---------+            +-------------+
           |                    |       |
           +----VREF---->  TX_DATA  RX_DATA
                                |       |
                          +-----------+
                          | LIN       |
                          | Controller|<---> SPI Slave <---> SPI Bus
                          +-----------+
                                |
                          +-----------+
                          | Register  |
                          | File      |
                          +-----------+
```

## Supply Architecture

| Rail | Source | Voltage | Load | Current |
|------|--------|---------|------|---------|
| VBAT | External | 8-18V | LDO inputs | 80mA max |
| VDD_LIN | LDO_LIN | 5.0V | LIN TX driver | 40mA |
| VDD_IO | LDO_ANA | 3.3V | Bandgap, I/O pads | 50mA |
| VDD_CORE | LDO_DIG | 1.8V | Digital logic | 30mA |
| VREF | Bandgap | 1.2V | LDO references | < 1mA |

## Pin List

| Pin | Direction | Type | Description |
|-----|-----------|------|-------------|
| VBAT | Input | Power | Battery supply 8-18V |
| GND | Input | Ground | Chip ground |
| LIN | I/O | Analog | LIN bus connection |
| SPI_CLK | Input | Digital | SPI clock |
| SPI_MOSI | Input | Digital | SPI data in |
| SPI_MISO | Output | Digital | SPI data out |
| SPI_CS_N | Input | Digital | SPI chip select |
| EN | Input | Digital | Global enable |
| WAKE | Output | Digital | Wake-up indicator |

## Block Inventory

| # | Block | Type | Generator | Transistors | Status |
|---|-------|------|-----------|-------------|--------|
| 1 | Bandgap Reference | Analog | bandgap_ref | 7 | Generated |
| 2 | LDO Analog 3.3V | Analog | ldo_analog | 8 | Generated |
| 3 | LDO Digital 1.8V | Analog | ldo_digital | 8 | Generated |
| 4 | LDO LIN 5.0V | Analog | ldo_lin | 8 | Generated |
| 5 | LIN Transceiver | Mixed | lin_transceiver | 12 | Generated |
| 6 | SPI Slave | Digital | RTL | - | RTL |
| 7 | LIN Controller | Digital | RTL | - | RTL |

## Connectivity Matrix

| From | To | Signal | Type |
|------|----|--------|------|
| Bandgap.VREF | LDO_ANA.VREF | VREF | Analog |
| Bandgap.VREF | LDO_DIG.VREF | VREF | Analog |
| Bandgap.VREF | LDO_LIN.VREF | VREF | Analog |
| LDO_ANA.VOUT | LDO_DIG.VIN | VDD_IO | Power |
| LDO_ANA.VOUT | Bandgap.VDD | VDD_IO | Power |
| LDO_LIN.VOUT | Transceiver.VDD | VDD_LIN | Power |
| LIN_Controller.TX_DATA | Transceiver.TXD | tx_data | Digital |
| Transceiver.RXD | LIN_Controller.RX_DATA | rx_data | Digital |
| SPI.ADDR/DATA | Register_File | reg_bus | Digital |
