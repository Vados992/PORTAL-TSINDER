"""Passive transmission-line calculations and calibrated measured trace analysis."""
import cmath
import csv
import io
import math
from .contracts import number
from .physics import C


def transmission_line(frequencies, length_m=1.0, L_H_m=250e-9, C_F_m=100e-12,
                      R_ohm_m=0.1, G_siemens_m=0.0, reference_ohm=50.0):
    for name, v, low, high in [("length", length_m, 0, 1e6), ("L", L_H_m, 1e-15, 1),
        ("C", C_F_m, 1e-18, 1), ("R", R_ohm_m, 0, 1e6), ("G", G_siemens_m, 0, 1e3),
        ("reference", reference_ohm, 1e-6, 1e6)]:
        number(v, name, low, high)
    if 1/math.sqrt(L_H_m*C_F_m) > C*(1+1e-12):
        raise ValueError("this passive-line benchmark requires wave speed <= c")
    if not 2 <= len(frequencies) <= 2000:
        raise ValueError("2..2000 frequencies required")
    rows = []
    for f in frequencies:
        number(f, "frequency", 1e-9, 1e15)
        w = 2*math.pi*f
        z, y = R_ohm_m+1j*w*L_H_m, G_siemens_m+1j*w*C_F_m
        gamma, impedance = cmath.sqrt(z*y), cmath.sqrt(z/y)
        if (gamma*length_m).real > 300:
            raise ValueError("attenuation outside representable range")
        A = cmath.cosh(gamma*length_m)
        B = impedance*cmath.sinh(gamma*length_m)
        D = cmath.sinh(gamma*length_m)/impedance
        denominator = 2*A+B/reference_ohm+D*reference_ohm
        s21 = 2/denominator
        s11 = (B/reference_ohm-D*reference_ohm)/denominator
        rows.append({"frequency_hz": f, "s21_real": s21.real, "s21_imag": s21.imag,
                     "s11_real": s11.real, "s11_imag": s11.imag})
    result = analyze(rows)
    result.update(origin="SYNTHETIC_RLGC_MODEL", phase_velocity_m_s=1/math.sqrt(L_H_m*C_F_m),
                  physical_aperture_evidence=False)
    return result


def parse_csv(text):
    if len(text.encode()) > 1_000_000:
        raise ValueError("CSV limit 1 MB")
    reader = csv.DictReader(io.StringIO(text))
    required = {"frequency_hz", "s21_real", "s21_imag"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("CSV requires frequency_hz,s21_real,s21_imag")
    rows = []
    for row in reader:
        if len(rows) >= 2000:
            raise ValueError("CSV limit 2000 rows")
        rows.append({k: float(row[k]) for k in required})
    return rows


def analyze(rows, calibration=None):
    if not 2 <= len(rows) <= 2000:
        raise ValueError("2..2000 ordered samples required")
    if calibration is not None and len(calibration) != len(rows):
        raise ValueError("calibration grid must match")
    result, phases, fs = [], [], []
    for index, row in enumerate(rows):
        f = number(row["frequency_hz"], "frequency", 1e-9, 1e15)
        if fs and f <= fs[-1]:
            raise ValueError("frequencies must be strictly increasing")
        z = complex(number(row["s21_real"], "real", -1e9, 1e9),
                    number(row["s21_imag"], "imag", -1e9, 1e9))
        if calibration is not None:
            ref = calibration[index]
            if ref["frequency_hz"] != f:
                raise ValueError("calibration frequency mismatch")
            reference = complex(number(ref["s21_real"], "calibration real", -1e9, 1e9),
                                number(ref["s21_imag"], "calibration imag", -1e9, 1e9))
            if abs(reference) < 1e-15:
                raise ValueError("calibration transfer is zero")
            z /= reference
        if abs(z) < 1e-15:
            raise ValueError("phase/group delay undefined for vanishing transfer")
        phase = cmath.phase(z)
        if phases:
            phase += 2*math.pi*round((phases[-1]-phase)/(2*math.pi))
        phases.append(phase)
        fs.append(f)
        result.append({"frequency_hz": f, "amplitude": abs(z), "gain_db": 20*math.log10(abs(z)),
                       "phase_rad": phase, "s21_real": z.real, "s21_imag": z.imag})
    for i in range(len(result)):
        lo, hi = max(0, i-1), min(len(result)-1, i+1)
        result[i]["group_delay_s"] = -(phases[hi]-phases[lo])/(2*math.pi*(fs[hi]-fs[lo]))
    return {"scope": "SIGNAL_TRANSFER_ONLY", "samples": result,
            "mean_group_delay_s": sum(v["group_delay_s"] for v in result)/len(result),
            "calibrated": calibration is not None,
            "sampling_assumption": "true phase increment between adjacent frequencies < pi",
            "spacetime_evidence": False}
