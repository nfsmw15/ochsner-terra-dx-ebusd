#!/usr/bin/env python3
"""Decode temscan.py results.

Response layout (10 data bytes after length byte 0a):
  pn(LE16) type unit max(SIN) min(SIN) value(2 bytes)
  pn: bit15/bit14 flags, bits 7..13 group, bits 0..6 parameter -> "GG-PPP"

Usage: temdecode.py RESULT.jsonl [RESULT.jsonl ...]
"""
import csv, glob, json, os, re, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

TYPES = {0: "none", 2: "on_off", 4: "time", 9: "selection", 13: "temp", 29: "counter",
         64: "duration", 77: "temp_threshold", 141: "temp_set", 192: "range"}
UNITS = {0: "", 2: "°C", 4: "K", 8: "%", 10: "h", 12: "min", 16: "kW", 18: "kWh", 42: "hh:mm",
         52: "l/min", 60: "MWh"}


def load_names():
    """GG-PPP -> (name, comment, values) from all known csv files."""
    names = {}
    files = glob.glob(os.path.join(ROOT, "ebusd-configuration/de/**/*.csv"), recursive=True)
    files += glob.glob(os.path.join(ROOT, "ha-live/*.csv"))
    for f in files:
        with open(f, encoding="utf-8", errors="replace") as fh:
            for row in csv.reader(fh):
                if len(row) < 9:
                    continue
                text = " ".join(row[2:5])
                m = re.search(r"(\d{2})-(\d{3})", text)
                if not m:
                    continue
                key = m.group(0)
                values = ""
                for cell in row[9:]:
                    if re.match(r"^\d+=", cell) and "Datentyp" not in cell and "0=none;2=" not in cell:
                        values = cell
                cur = names.get(key)
                if cur is None:
                    names[key] = (row[3], row[4], values)
                elif values.count(";") > cur[2].count(";"):
                    names[key] = (cur[0], cur[1], values)  # keep the most complete value list
    return names


def decode(r):
    b = bytes.fromhex(r)
    if len(b) < 11 or b[0] != 0x0a:
        return None
    pn = b[1] | (b[2] << 8)
    flags = pn >> 14
    group = (pn >> 7) & 0x7f
    param = pn & 0x7f
    typ, unit = b[3], b[4]
    mx, mn = struct.unpack("<hh", b[5:9])
    raw = b[9:11]
    d = {"pn": "%02d-%03d" % (group, param), "flags": flags, "type": typ, "unit": unit,
         "max": mx, "min": mn, "raw": raw.hex(), "sin": struct.unpack("<h", raw)[0]}
    if typ == 0x1d:
        # counter: kind (1=count: HCD:4, 2=hours: minute byte + HCD:3), bytes are 0..99 each
        hcd = lambda bs: sum(x * 100 ** i for i, x in enumerate(bs))
        kind = b[5]
        if kind == 2:
            d["sin"] = hcd(b[8:11])
            d["raw"] = "%dh %dmin" % (d["sin"], b[7])
        else:
            d["sin"] = hcd(b[7:11])
            d["raw"] = "count"
        d["max"] = d["min"] = kind
    return d


def main():
    names = load_names()
    seen = {}
    for f in sys.argv[1:]:
        for l in open(f):
            j = json.loads(l)
            if j["ok"]:
                seen[j["id"]] = j["r"]
    for ident in sorted(seen):
        d = decode(seen[ident])
        if not d:
            print(ident, "?", seen[ident])
            continue
        n = names.get(d["pn"], ("", "", ""))
        print("%s %s f%d %-12s %-5s max=%6d min=%6d raw=%s (%6d)  %s | %s" % (
            ident, d["pn"], d["flags"], TYPES.get(d["type"], d["type"]), UNITS.get(d["unit"], d["unit"]),
            d["max"], d["min"], d["raw"], d["sin"], n[0], n[1]))


if __name__ == "__main__":
    main()
