#!/usr/bin/env python3
"""Reproduce the paper's headline measurements from the released records.

Every check ASSERTS bit-exact agreement with the released value, so a regression
fails loudly rather than printing a number nobody reads.

Four reconstruction details matter, each of which costs a debugging session if
you rediscover it:
  * the loss table is CODE-MAJOR (atom index varies fastest within a code block);
  * the Eq-(6) radius carries a Hoeffding variance factor of 4;
  * the batteries accumulate the paired mean with exact summation, which numpy's
    pairwise mean() reproduces only to within about 1 ulp -- use math.fsum;
  * the two substrates have different geometries and different record schemas.
    Remote sensing is 35 codes x 9216 atoms, uint16 draw indices, and names code
    pairs directly as integers. Walsh acquisition is 49 codes x 73 intensities,
    uint8 indices, and names configurations as [k, e] pairs that must be mapped
    to table row order.
"""
import json, math, pathlib, re
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
EPS_FLOOR, HOEFFDING_VARIANCE = 1e-3, 4.0
STRIDE = 32768


def f(x):
    return float.fromhex(x) if isinstance(x, str) and x.startswith(("0x", "-0x")) else float(x)


def results_dir(name):
    return ROOT / "data" / name / "results"


def replay(name, n_codes):
    res = results_dir(name)
    table = np.fromfile(res / "loss_table.f64", dtype="<f8")
    assert table.size % n_codes == 0, f"loss table {table.size} not divisible by {n_codes}"
    natoms = table.size // n_codes
    streams = np.fromfile(res / "draw_streams.bin", dtype="<u2" if natoms > 256 else "<u1")
    assert int(streams.max()) < natoms, f"draw index {streams.max()} exceeds {natoms} atoms"

    record = json.load(open(res / "records.json"))
    rounds, kl = record["rounds"], record["kl_floored_uniform"]

    if "parent" in rounds[0]:                      # Walsh schema
        seen = sorted({tuple(r[k]) for r in rounds for k in ("parent", "successor")})
        assert len(seen) == n_codes, f"{len(seen)} configurations, expected {n_codes}"
        row = {c: i for i, c in enumerate(seen)}
        pair = lambda r: (row[tuple(r["parent"])], row[tuple(r["successor"])])
    else:                                          # remote-sensing schema
        pair = lambda r: (r["a"], r["b"])

    for i, rd in enumerate(rounds):
        n = rd["n_stop"]
        a, b = pair(rd)
        idx = streams[i * STRIDE: i * STRIDE + n].astype(np.int64)
        contrast = table[b * natoms + idx] - table[a * natoms + idx]
        released = f(rd.get("delta_hat_hex", rd["delta_hat"]))
        assert math.fsum(contrast) / n == released, f"{name} round {i}: paired mean differs"

        if "r_raw_hex" in rd:
            scale, alpha = f(rd["scale"]), f(rd["alpha_side"])
            variance_term = n * (HOEFFDING_VARIANCE * scale * scale / 2.0)
            radius = (kl + np.log(1.0 / alpha) + variance_term) / (scale * n)
            assert radius / (1.0 - EPS_FLOOR) == f(rd["r_raw_hex"]), f"{name} round {i}: radius differs"
    return len(rounds)


def held_out(name):
    text = (results_dir(name) / "primary.tsv").read_text()
    hits = dict(re.findall(r"(D_(?:5|10|100)(?:_sq|_npairs)?)\s+(\S+)", text))
    out = {}
    for m in (5, 10, 100):
        key = f"D_{m}_sq" if f"D_{m}_sq" in hits else f"D_{m}"
        v = f(hits[key])
        out[m] = (v ** 0.5 if key.endswith("_sq") else v) * 100
    return out


if __name__ == "__main__":
    for name, k in (("w_sr_battery_20260824", 35), ("w2_spi_battery_20260824", 49)):
        n = replay(name, k)
        print(f"{name}: {n}/{n} rounds reproduce the released values exactly")

    remote, walsh = held_out("w_sr_battery_20260824"), held_out("w2_spi_battery_20260824")
    assert remote[5] > remote[100], "remote-sensing held-out error should fall with budget"
    assert walsh[5] < walsh[100], "Walsh held-out error should rise with budget"
    print(f"remote sensing:    {remote[5]:.4f}% -> {remote[10]:.4f}% -> {remote[100]:.4f}%")
    print(f"Walsh acquisition: {walsh[5]:.4f}% -> {walsh[10]:.4f}% -> {walsh[100]:.4f}%")
    print("The substrates run in opposite directions. Held-out error is normalized over the")
    print("held-out set, whose size grows with the budget, so the two series are not a")
    print("like-for-like trend and are not read against one another.")
