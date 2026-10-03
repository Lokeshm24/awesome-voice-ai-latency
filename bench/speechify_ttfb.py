#!/usr/bin/env python3
"""Client-side TTFB benchmark for Speechify POST /v1/audio/stream (stdlib only).

Usage: SPEECHIFY_API_KEY=... python3 speechify_ttfb.py [--requests 1000] [--out results.csv]
Run it from a US-East host so the reading matches the benchmark's stated region.
"""

import argparse
import csv
import http.client
import json
import os
import re
import ssl
import statistics
import sys
import time
from datetime import datetime, timezone

HOST = "api.speechify.ai"
PATH = "/v1/audio/stream"
MODEL = "simba-3.2"
VOICE_ID = "geffen_32"
ACCEPT = "audio/pcm"  # raw 16-bit LE PCM, 24 kHz mono
TEXT = "Thanks for calling. Your order shipped this morning and should arrive at your door by Thursday."
MAX_ERRORS = 20
MIN_INTERVAL_S = 1.0
READ_SIZE = 65536

FIELDS = ["index", "utc_timestamp", "http_status", "ttfb_ms", "total_ms", "bytes", "new_connection",
          "server_timing_ttfb_ms", "error", "text_index", "text_chars", "text"]

MIN_CHARS, MAX_CHARS = 90, 110
SEED = 20261001

NAMES = ["Maria", "James", "Priya", "Daniel", "Aisha", "Tom", "Elena", "Marcus", "Sofia", "Kenji",
         "Laura", "Omar", "Grace", "Lucas", "Nina", "Peter", "Hannah", "Diego", "Chloe", "Samuel"]
SURNAMES = ["Patel", "Nguyen", "Garcia", "Thompson", "Okafor", "Fischer", "Rossi", "Kim", "Bennett", "Morales"]
CITIES = ["Denver", "Boston", "Austin", "Seattle", "Chicago", "Atlanta", "Portland", "Phoenix", "Nashville",
          "San Diego", "Toronto", "Dublin"]
STREETS = ["Maple St.", "Oak Ave.", "Main St.", "Harbor Blvd.", "Elm St.", "Pine Ave.", "Lake Dr.", "Cedar Rd."]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MORNING = ["7:30 a.m.", "8:15 a.m.", "8:45 a.m.", "9:00 a.m.", "9:30 a.m.", "10:15 a.m.", "10:45 a.m.", "11:30 a.m."]
AFTERNOON = ["12:15 p.m.", "1:20 p.m.", "2:00 p.m.", "2:45 p.m.", "3:40 p.m.", "4:15 p.m."]
EVENING = ["5:30 p.m.", "6:00 p.m.", "6:45 p.m.", "7:15 p.m.", "7:30 p.m.", "8:00 p.m."]
TIMES = MORNING + AFTERNOON + EVENING
FLOORS = ["second", "third", "fourth", "fifth", "sixth"]
RACES = [(5, 19, 34), (10, 41, 66), (21, 95, 140)]

TEMPLATES = [
    "Hi {name}, this is a reminder that your appointment with Dr. {surname} is at {time} on {month} {day}.",
    "Your package from our {city} warehouse shipped this morning and should arrive at {n3} {street} by {weekday}.",
    "The {city} office will close early on {month} {day}, so please submit your expense reports by {pm} that day.",
    "Tomorrow in {city}, expect a high of {temp} degrees with light winds and a {pct} percent chance of rain.",
    "Flight {n4} to {city} is now boarding at gate {gate}, and the cabin doors will close at {time} sharp.",
    "{name} finished the {race} kilometer race in {racemins} minutes and {secs} seconds, a new personal best.",
    "Preheat the oven to {oven} degrees, then bake the bread for about {mins} minutes until the crust is golden.",
    "Thanks for calling, {name}. Your balance is ${dollars}.{cents}, and the next payment is due on {month} {day}.",
    "The museum on {street} is open from {am} until six, and tickets cost ${price} for adults on weekdays.",
    "Our team meeting moved to {weekday} at {time} in room {room}, so please update your calendar invite.",
    "The library will host a free reading workshop for kids on {month} {day}, starting at {am} in the main hall.",
    "{name} said the new bike lane on {street} cut their commute by about {save} minutes each way this spring.",
    "Train {n3} to {city} departs from platform {gate} at {time}, with a short stop in {city2} along the way.",
    "{name}, please water the tomato plants twice a week and add about {liters} liters during the hottest days.",
    "The quarterly report shows revenue grew {pct} percent to ${mil} million, mostly from new customers in {city}.",
    "Your table for {party} at the bistro on {street} is booked for {weekday} at {eve}, and parking is free.",
    "About {crowd} people attended the outdoor concert in {city} on {month} {day}, despite the cool evening air.",
    "Ms. {surname} will teach the evening pottery class on {weekday} from {eve} until about ten o'clock.",
    "Room {room} on the {floor} floor has a projector, a whiteboard, and seating for up to {seats} people.",
    "The hiking trail near {city} is {dist}.{tenth} miles long and climbs about {feet} feet, so bring water.",
    "Invoice No. {inv} for ${dollars}.{cents} was paid on {month} {day}, and a receipt was sent to your email.",
    "The farmers market on {street} returns on {month} {day} with fresh bread, local honey, and {n2} new vendors.",
    "Mr. {surname} confirmed that the school bus will pick up students at {n3} {street} at {am} on {weekday}.",
    "The {city} branch extended its hours, so you can now visit us until {eve} on {weekday} evenings.",
    "{name} recommended the small cafe near {street} for its quiet tables, strong coffee, and fresh pastries.",
    "The {city} team shared a short update on the community garden, and everyone agreed to meet again soon.",
    "If you have questions about your reservation in {city}, reply to this message and someone will help you.",
    "{name} and {name2} are planning a quiet weekend in {city}, with a long walk by the water and dinner out.",
    "Thanks for your patience, {name}. We found your missing order and will send a replacement on {weekday}.",
    "Before you leave the house, {name}, remember to pack an umbrella because the skies over {city} look gray.",
    "The bakery on {street} now sells sourdough every {weekday}, and the first loaves usually sell out by noon.",
    "Our support team in {city} is available every {weekday} to answer any questions about your new plan.",
]


class _Lcg:
    """64-bit LCG so the generated texts are identical on any Python version."""

    def __init__(self, seed):
        self.state = seed & 0xFFFFFFFFFFFFFFFF

    def below(self, n):
        self.state = (self.state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        return (self.state >> 33) % n

    def pick(self, seq):
        return seq[self.below(len(seq))]

    def between(self, lo, hi):
        return lo + self.below(hi - lo + 1)


def varied_texts(count, seed=SEED):
    rng = _Lcg(seed)
    seen, texts = {TEXT}, []
    while len(texts) < count:
        city, name = rng.pick(CITIES), rng.pick(NAMES)
        race, lo, hi = rng.pick(RACES)
        slots = {
            "name": name, "name2": rng.pick([n for n in NAMES if n != name]), "surname": rng.pick(SURNAMES),
            "city": city, "race": race, "racemins": rng.between(lo, hi),
            "city2": rng.pick([c for c in CITIES if c != city]), "street": rng.pick(STREETS),
            "month": rng.pick(MONTHS), "day": rng.between(1, 28), "weekday": rng.pick(WEEKDAYS),
            "time": rng.pick(TIMES), "am": rng.pick(MORNING), "pm": rng.pick(AFTERNOON), "eve": rng.pick(EVENING),
            "floor": rng.pick(FLOORS), "n2": rng.between(12, 40), "save": rng.between(5, 20),
            "n3": rng.between(101, 989), "n4": rng.between(1020, 2980), "temp": rng.between(48, 91),
            "pct": rng.between(5, 60), "gate": rng.between(2, 38), "dist": rng.between(3, 12),
            "tenth": rng.between(1, 9), "mins": rng.between(18, 55), "secs": rng.between(10, 59),
            "oven": rng.pick([350, 375, 400, 425, 450]), "dollars": rng.between(24, 980),
            "cents": f"{rng.between(0, 99):02d}", "price": rng.between(12, 29), "room": rng.between(101, 640),
            "liters": rng.between(2, 9), "mil": rng.between(12, 95), "party": rng.pick(["two", "three", "four", "six"]),
            "crowd": f"{rng.between(3, 19) * 100 + rng.pick([0, 50]):,}", "seats": rng.between(8, 40),
            "feet": f"{rng.between(4, 30) * 100:,}", "inv": rng.between(10200, 98900),
        }
        text = rng.pick(TEMPLATES).format(**slots)
        if MIN_CHARS <= len(text) <= MAX_CHARS and text not in seen:
            seen.add(text)
            texts.append(text)
    return texts


def one_request(conn, body, headers, sink=None):
    new_connection = conn.sock is None
    ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    start = time.perf_counter()
    conn.request("POST", PATH, body=body, headers=headers)
    resp = conn.getresponse()
    ttfb_ms = None
    total_bytes = 0
    while True:
        chunk = resp.read1(READ_SIZE)
        if not chunk:
            break
        if ttfb_ms is None:
            ttfb_ms = (time.perf_counter() - start) * 1000
        total_bytes += len(chunk)
        if sink is not None:
            sink.write(chunk)
    total_ms = (time.perf_counter() - start) * 1000
    if resp.will_close:
        conn.close()
    match = re.search(r"ttfb;dur=([\d.]+)", resp.getheader("server-timing") or "")
    return {
        "content_type": resp.getheader("content-type") or "",
        "utc_timestamp": ts,
        "http_status": resp.status,
        "ttfb_ms": round(ttfb_ms, 2) if ttfb_ms is not None else "",
        "total_ms": round(total_ms, 2),
        "bytes": total_bytes,
        "new_connection": int(new_connection),
        "server_timing_ttfb_ms": match.group(1) if match else "",
        "error": "" if resp.status == 200 else f"HTTP {resp.status}",
    }


def percentile(sorted_vals, p):
    if not sorted_vals:
        return float("nan")
    k = (len(sorted_vals) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--requests", type=int, default=1000)
    ap.add_argument("--out", default="results.csv")
    ap.add_argument("--save-warmup", help="write the warm-up response body (raw PCM) to this path")
    ap.add_argument("--texts", choices=["varied", "fixed"], default="varied",
                    help="varied: a distinct generated sentence per request; fixed: TEXT every time")
    ap.add_argument("--start", type=int, default=0, help="first index into the varied text list")
    ap.add_argument("--print-texts", action="store_true", help="print the texts this run would send and exit")
    args = ap.parse_args()

    if args.texts == "varied":
        texts = varied_texts(args.start + args.requests)[args.start:]
        text_indices = range(args.start, args.start + args.requests)
    else:
        texts, text_indices = [TEXT] * args.requests, [-1] * args.requests
    if args.print_texts:
        for idx, text in zip(text_indices, texts):
            print(f"{idx}\t{len(text)}\t{text}")
        return

    key = os.environ.get("SPEECHIFY_API_KEY")
    if not key:
        sys.exit("SPEECHIFY_API_KEY is not set")

    def body_for(text):
        return json.dumps({"input": text, "voice_id": VOICE_ID, "model": MODEL}).encode()

    body = body_for(TEXT)
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": ACCEPT,
        "Connection": "keep-alive",
    }
    conn = http.client.HTTPSConnection(HOST, 443, timeout=30, context=ssl.create_default_context())

    if args.save_warmup:
        with open(args.save_warmup, "wb") as sink:
            warmup = one_request(conn, body, headers, sink)
    else:
        warmup = one_request(conn, body, headers)
    print(f"warm-up (discarded): status {warmup['http_status']}, content-type {warmup['content_type']!r}, "
          f"ttfb {warmup['ttfb_ms']} ms, {warmup['bytes']} bytes", flush=True)

    errors = 0
    ok_ttfb = []
    next_start = time.monotonic()
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for i, (text_index, text) in enumerate(zip(text_indices, texts), start=1):
            request_body = body_for(text)
            delay = next_start - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            next_start = time.monotonic() + MIN_INTERVAL_S
            try:
                row = one_request(conn, request_body, headers)
            except (http.client.HTTPException, OSError) as exc:
                conn.close()
                row = {
                    "utc_timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                    "http_status": 0, "ttfb_ms": "", "total_ms": "", "bytes": 0,
                    "new_connection": "", "server_timing_ttfb_ms": "", "error": type(exc).__name__,
                }
            row.update(index=i, text_index=text_index, text_chars=len(text), text=text)
            writer.writerow(row)
            f.flush()
            if row["error"]:
                errors += 1
                print(f"[{i}] error: {row['error']}", flush=True)
                if errors > MAX_ERRORS:
                    print(f"stopping: {errors} errors exceeds {MAX_ERRORS}", flush=True)
                    break
            else:
                ok_ttfb.append(row["ttfb_ms"])
            if i % 50 == 0:
                print(f"[{i}/{args.requests}] ok={len(ok_ttfb)} errors={errors} running median={statistics.median(ok_ttfb):.1f} ms", flush=True)

    s = sorted(ok_ttfb)
    print(f"done: n={len(s)} errors={errors} median={percentile(s, 50):.1f} p90={percentile(s, 90):.1f} "
          f"p95={percentile(s, 95):.1f} min={s[0] if s else 'nan'} max={s[-1] if s else 'nan'} ms", flush=True)


if __name__ == "__main__":
    main()
