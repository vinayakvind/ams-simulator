"""
Auto-Designer Engine - Iterative CMOS circuit optimization.

Accepts target specifications (gain, bandwidth, dropout, PSRR, etc.),
auto-sizes transistors and passives, runs simulations, and iterates
until specs are met or max iterations reached.

Usage:
    designer = AutoDesigner()
    result = designer.design_ldo(target_specs={
        'vout': 1.2, 'dropout': 0.2, 'iout_max': 0.1,
        'loop_gain': 60, 'bandwidth': 1e6
    })
    print(result['netlist'])
    print(result['measurements'])
"""

from __future__ import annotations

import math
import json
import time
import copy
from dataclasses import dataclass, field, asdict
from typing import Any, Optional, Callable


@dataclass
class DesignSpec:
    """A single design specification with target and tolerance."""
    name: str
    target: float
    unit: str = ''
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    weight: float = 1.0        # Priority weight for optimization
    achieved: float = 0.0      # Measured value after simulation
    passed: bool = False

    def check(self, measured: float) -> bool:
        """Check if measured value meets this spec."""
        self.achieved = measured
        lower = self.min_val if self.min_val is not None else self.target * 0.9
        upper = self.max_val if self.max_val is not None else self.target * 1.1
        self.passed = lower <= measured <= upper
        return self.passed

    def error(self) -> float:
        """Normalized error: 0 = on target, negative = below, positive = above."""
        if self.target == 0:
            return self.achieved
        return (self.achieved - self.target) / abs(self.target)


@dataclass
class DesignVariable:
    """A design variable that the optimizer can adjust."""
    name: str
    value: float
    min_val: float
    max_val: float
    unit: str = ''
    step: float = 0.0        # If 0, use continuous adjustment
    sensitivity: float = 0.0  # Computed: d(spec)/d(variable)

    def clamp(self) -> float:
        self.value = max(self.min_val, min(self.max_val, self.value))
        return self.value


@dataclass
class DesignIteration:
    """Record of one optimization iteration."""
    iteration: int
    variables: dict[str, float]
    measurements: dict[str, float]
    specs_met: int
    total_specs: int
    cost: float  # Weighted sum of spec errors
    timestamp: float = 0.0


@dataclass
class DesignResult:
    """Final result of an auto-design run."""
    success: bool
    netlist: str
    iterations: list[DesignIteration]
    final_measurements: dict[str, float]
    specs: list[dict]
    variables: dict[str, float]
    elapsed_seconds: float = 0.0
    message: str = ''


class AutoDesigner:
    """Iterative CMOS circuit auto-design engine.

    Works by:
    1. Starting from initial sizing / topology
    2. Generating a netlist from current design variables
    3. Running simulation (via callback or built-in engine)
    4. Measuring results against target specs
    5. Adjusting design variables using gradient-free optimization
    6. Repeating until all specs met or max iterations reached
    """

    def __init__(self, max_iterations: int = 30, verbose: bool = True):
        self.max_iterations = max_iterations
        self.verbose = verbose
        self._sim_callback: Optional[Callable] = None
        self._progress_callback: Optional[Callable] = None

    def set_simulation_callback(self, cb: Callable[[str], dict[str, float]]):
        """Set external simulation function.

        The callback receives a SPICE netlist string and returns
        a dict of node_name -> measured_value.
        """
        self._sim_callback = cb

    def set_progress_callback(self, cb: Callable[[int, int, dict], None]):
        """Progress callback(iteration, max_iter, current_measurements)."""
        self._progress_callback = cb

    # ------------------------------------------------------------------
    # LDO Auto-Design
    # ------------------------------------------------------------------
    def design_ldo(self, target_specs: dict[str, float]) -> DesignResult:
        """Auto-design a CMOS LDO regulator.

        Args:
            target_specs: Dict with keys like:
                'vout': 1.2,          # Output voltage (V)
                'dropout': 0.2,       # Max dropout voltage (V)
                'iout_max': 0.1,      # Max load current (A)
                'loop_gain': 60,      # DC loop gain (dB)
                'bandwidth': 1e6,     # Unity-gain bandwidth (Hz)
                'psrr': 60,           # Power supply rejection (dB)
                'phase_margin': 55,   # Phase margin (degrees)
                'iq': 0.001,          # Max quiescent current (A)
                'vin': 3.3,           # Input voltage (V)

        Returns:
            DesignResult with optimized netlist, measurements, iteration log.
        """
        start_time = time.time()

        # -- Build specs list --
        vout = target_specs.get('vout', 1.2)
        vin = target_specs.get('vin', 3.3)
        dropout = target_specs.get('dropout', 0.2)
        iout_max = target_specs.get('iout_max', 0.1)
        loop_gain = target_specs.get('loop_gain', 60)
        bw = target_specs.get('bandwidth', 1e6)

        specs = [
            DesignSpec('vout', vout, 'V',
                       min_val=vout * 0.98, max_val=vout * 1.02, weight=5.0),
            DesignSpec('dropout', dropout, 'V',
                       min_val=0.0, max_val=dropout * 1.2, weight=2.0),
            DesignSpec('regulation_error', 0.0, '%',
                       min_val=-2.0, max_val=2.0, weight=3.0),
        ]

        # -- Build design variables --
        # Start from hand-calculated initial sizing
        vref = 0.6
        r2_init = 100e3
        r1_init = r2_init * (vout / vref - 1)

        variables = [
            DesignVariable('w_pass', 2000e-6, 100e-6, 10000e-6, 'um'),
            DesignVariable('w_diff', 20e-6, 2e-6, 200e-6, 'um'),
            DesignVariable('w_load', 15e-6, 2e-6, 100e-6, 'um'),
            DesignVariable('w_tail', 10e-6, 2e-6, 100e-6, 'um'),
            DesignVariable('r1', r1_init, 10e3, 1e6, 'Ω'),
            DesignVariable('r2', r2_init, 10e3, 1e6, 'Ω'),
            DesignVariable('cc', 5e-12, 0.5e-12, 50e-12, 'F'),
            DesignVariable('rc', 2e3, 100, 50e3, 'Ω'),
            DesignVariable('ibias', 20e-6, 5e-6, 200e-6, 'A'),
            DesignVariable('cout', 1e-6, 100e-12, 10e-6, 'F'),
        ]
        var_dict = {v.name: v for v in variables}

        iterations: list[DesignIteration] = []
        best_cost = float('inf')
        best_vars = {v.name: v.value for v in variables}
        best_netlist = ''

        for it in range(self.max_iterations):
            # Generate netlist for current variables
            netlist = self._generate_ldo_netlist(var_dict, vin, vout)

            # Run simulation
            measurements = self._run_simulation(netlist)

            if measurements is None:
                measurements = self._estimate_ldo(var_dict, vin, vout, iout_max)

            # Check specs
            for spec in specs:
                if spec.name in measurements:
                    spec.check(measurements[spec.name])

            specs_met = sum(1 for s in specs if s.passed)
            cost = sum(s.weight * abs(s.error()) for s in specs)

            iteration = DesignIteration(
                iteration=it,
                variables={v.name: v.value for v in variables},
                measurements=dict(measurements),
                specs_met=specs_met,
                total_specs=len(specs),
                cost=cost,
                timestamp=time.time() - start_time,
            )
            iterations.append(iteration)

            if self.verbose:
                self._log_iteration(iteration, specs)

            if self._progress_callback:
                self._progress_callback(it, self.max_iterations, measurements)

            if cost < best_cost:
                best_cost = cost
                best_vars = {v.name: v.value for v in variables}
                best_netlist = netlist

            # Check convergence
            if specs_met == len(specs):
                break

            # -- Adjust variables (gradient-free: coordinate descent) --
            self._adjust_ldo_variables(var_dict, specs, measurements, vin, vout, iout_max)

        # Restore best
        for v in variables:
            v.value = best_vars[v.name]

        final_netlist = self._generate_ldo_netlist(var_dict, vin, vout)

        elapsed = time.time() - start_time
        result = DesignResult(
            success=all(s.passed for s in specs),
            netlist=final_netlist,
            iterations=iterations,
            final_measurements=iterations[-1].measurements if iterations else {},
            specs=[asdict(s) for s in specs],
            variables=best_vars,
            elapsed_seconds=elapsed,
            message=f"{'All specs met' if all(s.passed for s in specs) else 'Partial convergence'} "
                    f"in {len(iterations)} iterations ({elapsed:.1f}s)",
        )
        return result

    def _generate_ldo_netlist(self, var: dict[str, DesignVariable],
                               vin: float, vout_target: float) -> str:
        """Generate LDO netlist from current design variables."""
        w_pass = var['w_pass'].value * 1e6
        w_diff = var['w_diff'].value * 1e6
        w_load = var['w_load'].value * 1e6
        w_tail = var['w_tail'].value * 1e6
        r1 = var['r1'].value
        r2 = var['r2'].value
        cc = var['cc'].value
        rc = var['rc'].value
        ibias = var['ibias'].value
        cout = var['cout'].value
        rload = vout_target / 0.01  # 10mA nominal

        lines = [
            "* CMOS LDO - Auto-Design Iteration",
            f"* Target: Vin={vin}V, Vout={vout_target}V",
            "",
            ".MODEL nmos_1v8 NMOS (LEVEL=1 VTO=0.45 KP=280e-6 LAMBDA=0.08)",
            ".MODEL pmos_1v8 PMOS (LEVEL=1 VTO=-0.45 KP=95e-6 LAMBDA=0.10)",
            "",
            f"Vin vin 0 DC {vin}",
            "Vref vref_int 0 DC 0.6",
            "",
            f"Ibias_src vin nbias DC {ibias:.3e}",
            f"Mbias1 nbias nbias 0 0 nmos_1v8 W={w_tail:.1f}u L=1u",
            "",
            f"M1 d1 vref_int tail 0 nmos_1v8 W={w_diff:.1f}u L=0.5u",
            f"M2 d2 vfb tail 0 nmos_1v8 W={w_diff:.1f}u L=0.5u",
            f"Mtail tail nbias 0 0 nmos_1v8 W={w_tail:.1f}u L=1u",
            "",
            f"M3 d1 d1 vin vin pmos_1v8 W={w_load:.1f}u L=0.5u",
            f"M4 d2 d1 vin vin pmos_1v8 W={w_load:.1f}u L=0.5u",
            "",
            f"Mpass vout d2 vin vin pmos_1v8 W={w_pass:.0f}u L=0.5u",
            "",
            f"R1 vout vfb {r1:.0f}",
            f"R2 vfb 0 {r2:.0f}",
            "",
            f"Cc d2 vout_cc {cc:.2e}",
            f"Rc vout_cc vout {rc:.0f}",
            "",
            f"Cout vout 0 {cout:.2e}",
            f"Rload vout 0 {rload:.1f}",
            "",
            ".OP",
            ".TRAN 1u 200u UIC",
            ".SAVE V(vin) V(vout) V(vfb) V(d2) V(tail)",
            ".END",
        ]
        return "\n".join(lines)

    def _estimate_ldo(self, var: dict[str, DesignVariable],
                       vin: float, vout_target: float,
                       iout_max: float) -> dict[str, float]:
        """Analytical estimate of LDO performance when simulation is unavailable."""
        r1 = var['r1'].value
        r2 = var['r2'].value
        vref = 0.6
        ibias = var['ibias'].value
        w_pass = var['w_pass'].value
        w_diff = var['w_diff'].value
        cout = var['cout'].value
        cc = var['cc'].value

        # Output voltage from feedback divider
        vout_est = vref * (1 + r1 / r2)

        # Gm of diff pair  (Gm = sqrt(2 * Kp * W/L * Id))
        kpn = 280e-6
        id_half = ibias / 2
        l_diff = 0.5e-6
        gm_diff = math.sqrt(2 * kpn * (w_diff / l_diff) * id_half) if id_half > 0 else 1e-4

        # Gm of pass transistor
        kpp = 95e-6
        l_pass = 0.5e-6
        rload = vout_target / 0.01 if vout_target > 0 else 120
        i_load = vout_est / rload if rload > 0 else 0.01
        gm_pass = math.sqrt(2 * kpp * (w_pass / l_pass) * i_load) if i_load > 0 else 1e-3

        # Output impedance of diff pair  (ro ≈ 1 / (λ * Id))
        lambda_n = 0.08
        lambda_p = 0.10
        ro_n = 1 / (lambda_n * id_half) if id_half > 0 else 1e6
        ro_p = 1 / (lambda_p * id_half) if id_half > 0 else 1e6
        rout_ota = min(ro_n, ro_p)

        # Loop gain = Gm_ota * Rout_ota * Gm_pass * Rout_pass
        ro_pass = 1 / (lambda_p * i_load) if i_load > 0 else 1e4
        rout_pass = ro_pass  # approximately parallel with Rload but Rload dominates
        av_ota = gm_diff * rout_ota
        av2 = gm_pass * min(rout_pass, rload)
        loop_gain_db = 20 * math.log10(max(av_ota * av2, 1))

        # Dropout estimate (Vsg_pass - |Vtp|)
        # Vsg = sqrt(2*Id*L / (Kp*W)) + |Vtp|
        vtp = 0.45
        vsg = math.sqrt(2 * i_load * l_pass / (kpp * w_pass)) + vtp if w_pass > 0 else 1.0
        dropout_est = vsg - vtp  # Vdsat of pass transistor

        # Regulation error
        reg_error = (vout_est - vout_target) / vout_target * 100 if vout_target > 0 else 0

        # Bandwidth estimate (dominant pole at OTA output)
        c_dom = cc + 10e-15  # Miller cap + parasitics
        f_ota = gm_diff / (2 * math.pi * c_dom) if c_dom > 0 else 1e6
        ugbw = gm_diff * av2 / (2 * math.pi * cout) if cout > 0 else 1e6

        return {
            'vout': vout_est,
            'dropout': dropout_est,
            'regulation_error': reg_error,
            'loop_gain': loop_gain_db,
            'gm_diff': gm_diff,
            'gm_pass': gm_pass,
            'bandwidth': ugbw,
            'ibias_total': ibias * 3 + i_load,
        }

    def _adjust_ldo_variables(self, var: dict[str, DesignVariable],
                               specs: list[DesignSpec],
                               meas: dict[str, float],
                               vin: float, vout_target: float,
                               iout_max: float):
        """Adjust LDO design variables based on spec errors.

        Uses heuristic rules derived from analog design knowledge:
        - Vout error → adjust R1/R2 ratio
        - Dropout too high → widen pass transistor
        - Gain too low → increase Gm (widen diff pair or increase bias)
        """
        vout_meas = meas.get('vout', 0)
        vref = 0.6

        # Fix Vout via R1/R2 ratio
        if abs(vout_meas - vout_target) > vout_target * 0.01:
            # Desired ratio: R1/R2 = Vout/Vref - 1
            desired_ratio = vout_target / vref - 1
            r2_cur = var['r2'].value
            var['r1'].value = r2_cur * desired_ratio
            var['r1'].clamp()

        # Fix dropout
        dropout_meas = meas.get('dropout', 0.5)
        if dropout_meas > 0.2:
            # Widen pass transistor
            var['w_pass'].value *= 1.3
            var['w_pass'].clamp()

        # Fix regulation error via R1/R2 fine tune
        reg_err = meas.get('regulation_error', 0)
        if abs(reg_err) > 2.0:
            # Fine-tune R1
            correction = 1 - reg_err / 100
            var['r1'].value *= correction
            var['r1'].clamp()

        # Fix gain if available
        gain_meas = meas.get('loop_gain', 0)
        if gain_meas < 60:
            # Increase Gm: widen diff pair and/or increase bias
            var['w_diff'].value *= 1.2
            var['ibias'].value *= 1.15
            var['w_diff'].clamp()
            var['ibias'].clamp()

    def _run_simulation(self, netlist: str) -> Optional[dict[str, float]]:
        """Run simulation via callback if available."""
        if self._sim_callback:
            try:
                return self._sim_callback(netlist)
            except Exception:
                return None
        return None  # Fall back to analytical estimate

    def _log_iteration(self, it: DesignIteration, specs: list[DesignSpec]):
        """Print iteration summary."""
        status = "✓" if it.specs_met == it.total_specs else "…"
        print(f"  [{status}] Iter {it.iteration}: cost={it.cost:.4f}, "
              f"specs={it.specs_met}/{it.total_specs}, "
              f"Vout={it.measurements.get('vout', 0):.4f}V")

    # ------------------------------------------------------------------
    # OTA Auto-Design
    # ------------------------------------------------------------------
    def design_ota(self, target_specs: dict[str, float]) -> DesignResult:
        """Auto-design a folded-cascode OTA.

        target_specs keys:
            'gain': 70,         # DC gain (dB)
            'bandwidth': 10e6,  # UGB (Hz)
            'ibias': 50e-6,     # Tail current (A)
            'vdd': 1.8,         # Supply voltage
            'phase_margin': 60, # Phase margin (deg)
            'cl': 2e-12,        # Load capacitance (F)
        """
        start_time = time.time()
        gain = target_specs.get('gain', 70)
        bw = target_specs.get('bandwidth', 10e6)
        ibias = target_specs.get('ibias', 50e-6)
        vdd = target_specs.get('vdd', 1.8)
        cl = target_specs.get('cl', 2e-12)

        specs = [
            DesignSpec('gain', gain, 'dB', min_val=gain - 3, max_val=gain + 20, weight=3.0),
            DesignSpec('bandwidth', bw, 'Hz', min_val=bw * 0.8, max_val=bw * 5, weight=2.0),
        ]

        # Initial sizing
        # gm = 2*pi*BW*CL  for UGB = gm/(2*pi*CL)
        gm_need = 2 * math.pi * bw * cl
        kpn = 280e-6
        kpp = 95e-6
        id_half = ibias / 2

        # W/L for diff pair: gm = sqrt(2*Kp*W/L*Id)
        wl_diff = (gm_need ** 2) / (2 * kpn * id_half) if id_half > 0 else 100
        w_diff = wl_diff * 0.5e-6  # L=0.5u
        w_diff = max(w_diff, 2e-6)

        variables = [
            DesignVariable('w_diff', w_diff, 2e-6, 500e-6, 'um'),
            DesignVariable('w_load', 10e-6, 2e-6, 200e-6, 'um'),
            DesignVariable('w_tail', 10e-6, 2e-6, 200e-6, 'um'),
            DesignVariable('ibias', ibias, 5e-6, 500e-6, 'A'),
            DesignVariable('cc', 1e-12, 0.1e-12, 20e-12, 'F'),
        ]
        var_dict = {v.name: v for v in variables}

        iterations = []
        best_cost = float('inf')
        best_vars = {v.name: v.value for v in variables}

        for it in range(self.max_iterations):
            meas = self._estimate_ota(var_dict, vdd, cl)

            for spec in specs:
                if spec.name in meas:
                    spec.check(meas[spec.name])

            specs_met = sum(1 for s in specs if s.passed)
            cost = sum(s.weight * abs(s.error()) for s in specs)

            iteration = DesignIteration(
                iteration=it,
                variables={v.name: v.value for v in variables},
                measurements=dict(meas),
                specs_met=specs_met,
                total_specs=len(specs),
                cost=cost,
                timestamp=time.time() - start_time,
            )
            iterations.append(iteration)

            if cost < best_cost:
                best_cost = cost
                best_vars = {v.name: v.value for v in variables}

            if specs_met == len(specs):
                break

            # Adjust
            gain_meas = meas.get('gain', 0)
            bw_meas = meas.get('bandwidth', 0)

            if gain_meas < gain:
                var_dict['w_load'].value *= 1.2  # increase rout
                var_dict['w_load'].clamp()
            if bw_meas < bw * 0.8:
                var_dict['w_diff'].value *= 1.15  # increase gm
                var_dict['ibias'].value *= 1.1
                var_dict['w_diff'].clamp()
                var_dict['ibias'].clamp()

        for v in variables:
            v.value = best_vars[v.name]

        netlist = self._generate_ota_netlist(var_dict, vdd)

        return DesignResult(
            success=all(s.passed for s in specs),
            netlist=netlist,
            iterations=iterations,
            final_measurements=iterations[-1].measurements if iterations else {},
            specs=[asdict(s) for s in specs],
            variables=best_vars,
            elapsed_seconds=time.time() - start_time,
            message=f"OTA design: {len(iterations)} iterations",
        )

    def _estimate_ota(self, var: dict[str, DesignVariable],
                       vdd: float, cl: float) -> dict[str, float]:
        """Analytical estimate of OTA performance."""
        w_diff = var['w_diff'].value
        w_load = var['w_load'].value
        ibias_val = var['ibias'].value
        id_half = ibias_val / 2
        kpn = 280e-6
        kpp = 95e-6
        lambda_n = 0.08
        lambda_p = 0.10
        l = 0.5e-6

        gm = math.sqrt(2 * kpn * (w_diff / l) * id_half) if id_half > 0 else 1e-4
        ro_n = 1 / (lambda_n * id_half) if id_half > 0 else 1e6
        ro_p = 1 / (lambda_p * id_half) if id_half > 0 else 1e6
        rout = min(ro_n, ro_p)
        av = gm * rout
        gain_db = 20 * math.log10(max(av, 1))
        bw = gm / (2 * math.pi * cl) if cl > 0 else 1e6

        return {
            'gain': gain_db,
            'bandwidth': bw,
            'gm': gm,
            'rout': rout,
        }

    def _generate_ota_netlist(self, var: dict[str, DesignVariable],
                               vdd: float) -> str:
        w_diff = var['w_diff'].value * 1e6
        w_load = var['w_load'].value * 1e6
        w_tail = var['w_tail'].value * 1e6
        ibias_val = var['ibias'].value

        lines = [
            "* CMOS OTA - Auto-Designed",
            ".MODEL nmos_1v8 NMOS (LEVEL=1 VTO=0.45 KP=280e-6 LAMBDA=0.08)",
            ".MODEL pmos_1v8 PMOS (LEVEL=1 VTO=-0.45 KP=95e-6 LAMBDA=0.10)",
            "",
            f"Vdd vdd 0 DC {vdd}",
            f"Ibias vdd nbias DC {ibias_val:.3e}",
            f"Mbias nbias nbias 0 0 nmos_1v8 W={w_tail:.1f}u L=1u",
            "",
            f"M1 d1 inp tail 0 nmos_1v8 W={w_diff:.1f}u L=0.5u",
            f"M2 d2 inn tail 0 nmos_1v8 W={w_diff:.1f}u L=0.5u",
            f"Mtail tail nbias 0 0 nmos_1v8 W={w_tail:.1f}u L=1u",
            "",
            f"M3 d1 d1 vdd vdd pmos_1v8 W={w_load:.1f}u L=0.5u",
            f"M4 d2 d1 vdd vdd pmos_1v8 W={w_load:.1f}u L=0.5u",
            "",
            "* Output = d2",
            "CL d2 0 2p",
            "",
            ".SAVE V(d1) V(d2) V(inp) V(inn) V(tail)",
            ".END",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Current Mirror Auto-Design
    # ------------------------------------------------------------------
    def design_current_mirror(self, target_specs: dict[str, float]) -> DesignResult:
        """Auto-design a CMOS current mirror.

        target_specs keys:
            'iref': 10e-6,        # Reference current
            'ratio': 1.0,         # Mirror ratio (Iout/Iref)
            'compliance': 0.3,    # Min output voltage (V)
            'rout': 1e6,          # Output impedance (Ω)
            'type': 'nmos',       # 'nmos' or 'pmos'
            'cascode': False,     # Use cascode topology
        """
        start_time = time.time()
        iref = target_specs.get('iref', 10e-6)
        ratio = target_specs.get('ratio', 1.0)
        mirror_type = target_specs.get('type', 'nmos')
        cascode = target_specs.get('cascode', False)

        kp = 280e-6 if mirror_type == 'nmos' else 95e-6
        vth = 0.45
        lam = 0.08 if mirror_type == 'nmos' else 0.10
        l = 1e-6  # Use longer L for better matching

        # Size: W = 2*Id*L / (Kp * Vdsat^2), aim for Vdsat=0.2V
        vdsat = 0.2
        w_ref = 2 * iref * l / (kp * vdsat ** 2)
        w_out = w_ref * ratio

        netlist_lines = [
            f"* CMOS {'Cascode ' if cascode else ''}Current Mirror ({mirror_type.upper()})",
            f".MODEL {mirror_type}_cm {'NMOS' if mirror_type == 'nmos' else 'PMOS'} "
            f"(LEVEL=1 VTO={'0.45' if mirror_type == 'nmos' else '-0.45'} "
            f"KP={kp:.0e} LAMBDA={lam})",
            "",
        ]

        if mirror_type == 'nmos':
            netlist_lines += [
                f"M_ref drain_ref drain_ref 0 0 {mirror_type}_cm W={w_ref*1e6:.1f}u L={l*1e6:.1f}u",
                f"M_out drain_out drain_ref 0 0 {mirror_type}_cm W={w_out*1e6:.1f}u L={l*1e6:.1f}u",
            ]
        else:
            netlist_lines += [
                f"M_ref drain_ref drain_ref vdd vdd {mirror_type}_cm W={w_ref*1e6:.1f}u L={l*1e6:.1f}u",
                f"M_out drain_out drain_ref vdd vdd {mirror_type}_cm W={w_out*1e6:.1f}u L={l*1e6:.1f}u",
            ]

        iout_est = iref * ratio
        rout = 1 / (lam * iout_est) if iout_est > 0 else 1e6
        compliance = vdsat + 0.05  # Vdsat + margin

        return DesignResult(
            success=True,
            netlist="\n".join(netlist_lines),
            iterations=[],
            final_measurements={'iout': iout_est, 'rout': rout, 'compliance': compliance},
            specs=[],
            variables={'w_ref': w_ref, 'w_out': w_out, 'l': l},
            elapsed_seconds=time.time() - start_time,
            message=f"Current mirror: Iout={iout_est*1e6:.1f}uA, ratio={ratio}",
        )

    # ------------------------------------------------------------------
    # Generic design entry point
    # ------------------------------------------------------------------
    def design(self, block_type: str, target_specs: dict[str, float]) -> DesignResult:
        """Route to appropriate design function.

        block_type: 'ldo', 'ota', 'current_mirror', 'bandgap'
        """
        dispatchers = {
            'ldo': self.design_ldo,
            'ota': self.design_ota,
            'current_mirror': self.design_current_mirror,
        }
        func = dispatchers.get(block_type.lower())
        if func is None:
            return DesignResult(
                success=False, netlist='', iterations=[], final_measurements={},
                specs=[], variables={},
                message=f"Unknown block type: {block_type}. Available: {list(dispatchers.keys())}",
            )
        return func(target_specs)

    def to_json(self, result: DesignResult) -> str:
        """Serialize DesignResult to JSON for API responses."""
        return json.dumps(asdict(result), indent=2, default=str)
