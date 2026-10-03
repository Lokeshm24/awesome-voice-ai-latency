#!/usr/bin/env python3
"""Summarise a speechify_ttfb.py CSV: percentiles (linear interpolation), errors, UTC window, server/network split."""

import csv
import statistics
import sys


def pct(vals, p):
    s = sorted(vals)
    k = (len(s) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


rows = list(csv.DictReader(open(sys.argv[1])))
ok = [r for r in rows if r["http_status"] == "200" and r["ttfb_ms"]]
errors = [r for r in rows if r not in ok]
ttfb = [float(r["ttfb_ms"]) for r in ok]
total = [float(r["total_ms"]) for r in ok]
nbytes = [int(r["bytes"]) for r in ok]
server = [float(r["server_timing_ttfb_ms"]) for r in ok if r["server_timing_ttfb_ms"]]
network = [float(r["ttfb_ms"]) - float(r["server_timing_ttfb_ms"]) for r in ok if r["server_timing_ttfb_ms"]]
new_conn = sum(1 for r in ok if r["new_connection"] == "1")

print(f"rows={len(rows)} ok={len(ok)} errors={len(errors)} new_connection_rows={new_conn}")
print(f"window_utc={rows[0]['utc_timestamp']} .. {rows[-1]['utc_timestamp']}")
for name, v in [("client_ttfb_ms", ttfb), ("server_timing_ttfb_ms", server), ("network_and_client_ms", network), ("total_ms", total)]:
    if v:
        print(f"{name}: n={len(v)} median={pct(v, 50):.1f} p90={pct(v, 90):.1f} p95={pct(v, 95):.1f} "
              f"min={min(v):.1f} max={max(v):.1f} mean={statistics.fmean(v):.1f}")
print(f"bytes: median={statistics.median(nbytes):.0f} min={min(nbytes)} max={max(nbytes)} "
      f"(~{statistics.median(nbytes) / 48000:.2f} s of 24 kHz 16-bit mono)")
if errors:
    print("errors:", [(r["index"], r["http_status"], r["error"]) for r in errors])
