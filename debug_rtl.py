"""Debug script for RTL engine."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from simulator.engine.rtl_engine import RTLParser, RTLSimulator, BitVec

code = open('designs/lin_asic/rtl/lin_controller.v', encoding='utf-8').read()

# --- Parse check ---
p = RTLParser(code)
mod = p.parse_module()
print("Module:", mod.name)
print("Signals sample:", list(mod.signals.keys())[:10])
print("Always blocks:", len(mod.always_blocks))
for i, blk in enumerate(mod.always_blocks):
    print(f"  [{i}] sens={blk.sensitivity[:2]}, stmts={len(blk.body)}")
print("Localparams:", {k: v.to_int() for k, v in mod.localparams.items()})
print("Functions:", list(mod.functions.keys()))
print()

# --- Simulator setup ---
sim = RTLSimulator()
sim._clk_sig = 'clk'
sim._rst_sig = 'rst_n'
sim.load_verilog(code)

# Print widths
for k in ['reg_addr','reg_wdata','reg_wr','pid_reg','baud_div','baud_cnt','baud_tick','state']:
    w = sim._widths.get(k, 'MISSING')
    print(f"{k}: width={w}")

print()
sim.set_input('rxd', 1)
sim.set_input('lin_en', 1)
sim.set_input('master_mode', 0)
sim.set_input('baud_div', 16)
sim.set_input('reg_addr', 0)
sim.set_input('reg_wdata', 0)
sim.set_input('reg_wr', 0)
sim.set_input('reg_rd', 0)

sim.reset(cycles=3)
print("After reset:")
for k in ['state','pid_reg','baud_cnt','baud_tick','rst_n']:
    print(f"  {k}={sim.get_output(k)}")

# Register write
sim.set_input('reg_addr', 0x06)
sim.set_input('reg_wdata', 0x3C)
sim.set_input('reg_wr', 1)
print(f"Before tick: reg_wr={sim.get_output('reg_wr')}, reg_addr=0x{sim.get_output('reg_addr'):02X}")
sim.tick(1)
sim.set_input('reg_wr', 0)
sim.tick(1)
print(f"After tick: pid_reg=0x{sim.get_output('pid_reg'):02X}")

# Baud tick count
sim2 = RTLSimulator()
sim2._clk_sig = 'clk'
sim2._rst_sig = 'rst_n'
sim2.load_verilog(code)
sim2.set_input('rxd', 1)
sim2.set_input('lin_en', 1)
sim2.set_input('master_mode', 0)
sim2.set_input('baud_div', 8)
sim2.set_input('reg_addr', 0)
sim2.set_input('reg_wdata', 0)
sim2.set_input('reg_wr', 0)
sim2.set_input('reg_rd', 0)
sim2.reset(cycles=3)

ticks = 0
for _ in range(50):
    sim2.tick(1)
    if sim2.get_output('baud_tick'):
        ticks += 1
        print(f"  baud_tick at cycle {sim2._time//2}, baud_cnt={sim2.get_output('baud_cnt')}")

print(f"Total baud ticks in 50 cycles (div=8): {ticks}")

# Show block 0 (baud generator) AST
blk0 = sim._always_blocks[0]
print("\nBlock 0 body AST:", blk0.body[0])
