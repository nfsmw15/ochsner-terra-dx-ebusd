#!/usr/bin/env python3
"""Generate an ebusd CSV for the TEM/Ochsner controller from temscan.py results.

Usage: temgen.py OUT.csv SCAN.jsonl [SCAN.jsonl ...]

Response data layout (after length byte 0a):
  0-1 pn (LE16: flags<<14 | group<<7 | param)   2 type   3 unit
  4-5 max   6-7 min   8-9 value
1-byte types store max/min/value in the low byte of each pair; the high byte
of the min pair is the scale code (0 = 1, 1 = 0.5, 9 = 0.1).
"""
import csv, json, os, re, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import temdecode as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BLOCKS = {  # block -> (circuit, description); order = dedup priority
    0x02: ("Waermepumpe", "Wärmepumpe (WE_1)"),
    0x04: ("Zusatzheizung", "Zusatzheizung (WE_2)"),
    0x0a: ("Heizkreis", "Heizkreis (aktiv)"),
    0x0e: ("Warmwasserkreis", "Warmwasserkreis"),
    0x10: ("Waermemanager", "Wärmemanager (Puffer)"),
    0x12: ("Kaskadenmanager", "Kaskadenmanager"),
    0x00: ("Anlage", "Anlage"),
    0x08: ("Heizkreis_A", "Heizkreis A (inaktiv)"),
    0x0c: ("Heizkreis_C", "Heizkreis C (inaktiv)"),
}
# parameters that exist in every block but belong to the system
GLOBAL = {"00-000", "02-070", "02-071", "02-072", "02-073", "04-043", "04-045", "06-014", "01-094"}
# settings writable from Home Assistant; all other writable params get access level "install"
WRITABLE = {"02-070", "02-072", "03-001", "03-002", "03-012", "03-013", "03-021", "03-050", "03-051",
            "03-053", "05-000", "05-050", "05-051", "05-086", "06-027"}
INACTIVE = {"Heizkreis_A", "Heizkreis_C"}  # heating circuits with application type 0: read on demand only
ONE_BYTE = {0x00, 0x01, 0x80, 0xc1}
SIGNED_1B = {0x01, 0xc1}
SCALE = {0: 1, 1: 2, 9: 10}
DIV2 = {0x0d: 10, 0x4d: 10, 0x8d: 10, 0x03: 10, 0x0e: 100, 0x8e: 100}
UNIT = {2: "°C", 4: "K", 8: "%", 10: "h", 12: "min", 16: "kW", 18: "kWh", 52: "L/min", 60: "MWh"}
# poll priority: live values often, settings rarely, static never
LIVE = re.compile(r"^(00-|01-|02-05[0-5]|02-04|21-|23-|02-08)")
# polled first (r1): what the operating state view needs, per (block, parameter)
FAST = {(0x02, "02-053"), (0x02, "23-003"), (0x02, "00-007"), (0x02, "00-008"), (0x02, "01-076"),
        (0x02, "00-004"), (0x0e, "02-052"), (0x0e, "01-066"), (0x0e, "22-066"), (0x10, "00-015"),
        (0x10, "00-017"), (0x0a, "01-021"), (0x0a, "00-002"), (0x02, "21-002")}
ERRCODES = open(os.path.join(ROOT, "docs/errcodes.txt")).read().splitlines()[1]


def slug(text):
    text = text.replace("ß", "ss").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    text = text.replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"\b\d{2}-\d{3}\b", "", text)
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()[:40]


def load_notes():
    notes = {}
    with open(os.path.join(ROOT, "docs/display-notes.csv"), encoding="utf-8") as fh:
        for row in csv.reader(l for l in fh if not l.startswith("#")):
            if len(row) >= 4 and re.match(r"\d{2}-\d{3}", row[0]):
                notes[row[0]] = (row[2], row[3])
    return notes


def load_status():
    """(param, block) -> value list, highest priority source."""
    lists = {}
    with open(os.path.join(ROOT, "docs/status-lists.csv"), encoding="utf-8") as fh:
        for row in csv.reader(l for l in fh if not l.startswith("#")):
            if len(row) >= 3 and re.match(r"\d{2}-\d{3}", row[0]):
                lists[(row[0], int(row[1], 16))] = row[2].replace("*", "")
    return lists


def field_for(d, b, values):
    """Return list of ebusd field tuples (name, part, type, div/values, unit, comment)."""
    typ, unit = b[3], b[4]
    u = UNIT.get(unit, "")
    if typ == 0x1d:
        if b[5] == 2:
            return [("", "s", "IGN:6", "", "", ""), ("minutes", "s", "UCH", "", "min", ""),
                    ("", "s", "HCD:3", "", "h", "")]
        return [("", "s", "IGN:6", "", "", ""), ("", "s", "HCD:4", "", "", "")]
    if typ == 0x04:
        if unit == 40:
            return [("", "s", "IGN:8", "", "", ""), ("", "s", "UIN", "", "", "Tage seit 31.12.1899")]
        if unit == 42 and d["max"] == 1439:
            return [("", "s", "IGN:8", "", "", ""), ("", "s", "MIN", "", "", "")]
        return [("", "s", "IGN:8", "", "", ""), ("", "s", "UIN", "", u, "")]
    if typ in ONE_BYTE:
        div = SCALE.get(b[8], 1)
        t = "SCH" if typ in SIGNED_1B else "UCH"
        return [("", "s", "IGN:8", "", "", ""), ("", "s", t, values or (div if div > 1 else ""), u, "")]
    if typ == 0x02:
        # field name "onoff" lets the HA template map it to binary_sensor/switch
        if values:  # own texts: plain list sensor instead of a binary on/off
            return [("", "s", "IGN:8", "", "", ""), ("", "s", "UIN", values, "", "")]
        return [("", "s", "IGN:8", "", "", ""), ("onoff", "s", "UIN", "0=off;1=on", "", "")]
    if typ == 0x09:
        return [("", "s", "IGN:8", "", "", ""), ("", "s", "UIN", values, "", "")]
    div = DIV2.get(typ, "")
    return [("", "s", "IGN:8", "", "", ""), ("", "s", "SIN", div, u, "")]


def main():
    out, scans = sys.argv[1], sys.argv[2:]
    names, notes, status = T.load_names(), load_notes(), load_status()
    seen = {}
    for f in scans:
        for j in map(json.loads, open(f)):
            if j["ok"]:
                seen[j["id"]] = j["r"]

    # ids answering "invalid" (ff9f) at user level 0: only read/write them while 04-043 = 1 (Fachpartner),
    # otherwise ebusd would decode the invalid reply as value 0
    fp_only = set()
    lvl = os.path.join(ROOT, "scan/level0.jsonl")
    if os.path.exists(lvl):
        fp_only = {j["id"] for j in map(json.loads, open(lvl)) if j["r"][2:6] == "ff9f"}
    rows, done = [["*[fp]", "Anlage", "", "p04_043_ebene_einsteller", "", "", "", "", "", "", "", ""]], {}
    for blk in BLOCKS:
        circuit, desc = BLOCKS[blk]
        rows.append(["# " + desc])
        for ident in sorted(i for i in seen if int(i[6:8], 16) == 0x40 + blk):
            r = seen[ident]
            b = bytes.fromhex(r)
            if b[0] != 0x0a:
                continue  # text/list parameters are generated below
            d = T.decode(r)
            pn = d["pn"]
            key = (b[3], b[4], d["max"], d["min"])
            if b[3] == 0x1d or b[4] in (18, 60):
                key += (d["sin"] // 20,)  # counters: mirrored copies match, other devices differ
            if (pn in GLOBAL) != (blk == 0x00) and pn in GLOBAL:
                continue
            own = (pn, blk) in status  # own status per device, never a mirror
            if not own and key in done.get(pn, ()):
                continue  # same parameter mirrored from an earlier block
            done.setdefault(pn, set()).add(key)
            short, long_, values = names.get(pn, ("", "", ""))
            if pn in notes:
                long_ = notes[pn][0] or long_
                values = notes[pn][1] or values
            values = status.get((pn, blk), values)
            if values and b[3] == 0x09 and str(d["sin"]) not in {v.split("=")[0] for v in values.split(";")}:
                # list taken from another TEM device lacks the value this unit reports: keep it visible
                # (else HA drops the state as invalid enum option) until the display text is known
                values += ";%d=Wert_%d" % (d["sin"], d["sin"])
            title = re.sub(r"\s*\d{2}-\d{3}\s*", " ", long_ or short).strip().replace("_", " ") or "Unbekannt"
            name = "p%s_%s" % (pn.replace("-", "_"), slug(title) or "x")
            prio = "r" if circuit in INACTIVE else "r3" if LIVE.match(pn) and not d["flags"] & 1 else "r9"
            if (blk, pn) in FAST:
                prio = "r1"
            comment = "%s (%s)" % (title[0].upper() + title[1:], pn)
            fields = field_for(d, b, values if values and b[3] in (0x00, 0x02, 0x09) else "")
            if pn == "04-043":
                prio = "r1"  # access level drives the [fp] condition
            cond = "[fp=1]" if ident in fp_only else ""
            rows.append([cond + prio, circuit, "", name, comment, "", "15", "0621", ident] +
                        [x for f in fields for x in f])
            if d["flags"] & 1:
                # writes always carry 2 bytes LE, also for 1-byte fields (verified 02-072, 06-016)
                vt = fields[-1][2]
                vt = {"UCH": "UIN", "SCH": "SIN"}.get(vt, vt)
                level = "" if pn in WRITABLE and circuit not in INACTIVE else "install"
                rows.append([cond + "w", circuit, level, name, comment, "", "10", "0623", ident,
                             "", "", vt, fields[-1][3], fields[-1][4], ""])

    rows.append(["# Fehlerspeicher (Service Report / Störungsdaten) - Eintrag 1 = neuester"])
    temps = "TA TMK TPO TB TWV TWR TQE TQA TPV TSG_Verdampfer TSG_Kompressor THG SW PND PHD".split()
    for e in range(6):
        ids = ";".join("02da%d%d40" % (e, p) for p in range(4))
        f = [("quelle", "s", "UCH", "1=Wärmepumpe", "", ""), ("code", "s", "UCH", ERRCODES, "", "Störcode OTE"),
             ("datum", "s", "UIN", "", "", "Tage seit 31.12.1899"), ("zeit", "s", "UIN", "", "", "Minuten seit Montag 0:00"),
             ("status", "s", "UCH", "", "", "WP Status")]
        f += [(t.lower(), "s", "SIN", 10, "bar" if t in ("PND", "PHD") else "°C", "") for t in temps]
        rows.append(["r9", "Stoerungen", "", "eintrag%d" % (e + 1), "Störung %d" % (e + 1),
                     "", "15", "0622", ids] + [x for t in f for x in t])

    rows.append(["# Anmeldung Fachpartner-Ebene - 04-042 Passworteingabe an Master 10 - verifiziert 2026-10-23"])
    rows.append(["w", "Anlage", "", "passwort", "Passworteingabe (04-042)", "", "10", "0623", "04aa0040",
                 "", "", "UIN", "", "", ""])

    # TEM -> heat generator modules (03 = WE_1 heat pump, 13 = WE_2), sent cyclically; the module switches the
    # WW diverter itself from the operating mode byte (verified 2026-10-24: 1 during WW charge, 0 otherwise)
    rows.append(["# Anforderung an die Wärmeerzeuger-Module (passiv mitgelesen) - Betriebsart steuert das Umschaltventil"])
    for circuit, zz in (("Waermepumpe", "03"), ("Zusatzheizung", "13")):
        rows.append(["u", circuit, "", "anforderung", "Anforderung an Wärmeerzeuger", "10", zz, "0501", "",
                     "vorlaufsoll", "m", "D2B", "", "°C", "Vorlauf-Soll",
                     "", "m", "IGN:2", "", "", "",
                     "leistung", "m", "UCH", "", "%", "Leistungsanforderung",
                     "", "m", "IGN:1", "", "", "",
                     "freigabe", "m", "UCH", "", "", "",
                     "", "m", "IGN:2", "", "", "",
                     "betriebsart", "m", "UCH", "0=Heizen;1=Warmwasser", "", "Betriebsart / Stellung Umschaltventil"])

    # module -> TEM status reply (0503, block 01, 12 bytes), every ~8 s; decoded 2026-11-16 against TEM values and
    # SDM630 power: b1 state (2 = start-up ~30 s with pumps only), b2 outputs (0x40 pump incl. ~25 s overrun,
    # 0x08 compressor), b3 compressor %, b4 flow 0.5 °C (= TWV, faster), b5 return whole °C (= TWR, ff = none),
    # b6-b9 unknown constants (ff 3f 00 00 / ff 3f 43 00), b10 = 09-007 generator type, b11 unknown
    rows.append(["# Status der Wärmeerzeuger-Module an den TEM (passiv mitgelesen)"])
    for circuit, qq, state in (("Waermepumpe", "03", "0=Aus;1=Verdichter_ein;2=Anlauf"), ("Zusatzheizung", "13", "")):
        rows.append(["u", circuit, "", "modulstatus", "Status Wärmeerzeuger-Modul", qq, "10", "0503", "01",
                     "zustand", "m", "UCH", state, "", "Zustand Modul",
                     "verdichter", "m", "BI3", "0=aus;1=ein", "", "Verdichter",
                     "pumpe", "m", "BI6", "0=aus;1=ein", "", "Pumpe",
                     "leistung", "m", "UCH", "", "%", "Verdichterleistung",
                     "vorlauf", "m", "D1C", "", "°C", "Vorlauf",
                     "ruecklauf", "m", "UCH", "", "°C", "Rücklauf"])

    rows.append(["# Texte (Stammdaten)"])
    for pn, ident, title in [("04-090", "04da", "seriennummer"), ("04-095", "04df", "anlagenbetreiber"),
                             ("04-096", "04e0", "installateur"), ("04-097", "04e1", "planer")]:
        rows.append(["r9", "Anlage", "", title, "%s (%s)" % (title.capitalize(), pn), "", "15", "0622", "%s0040;%s0140" % (ident, ident),
                     "", "s", "STR:20", "", "", ""])

    with open(out, "w", newline="", encoding="utf-8") as fh:
        fh.write("type,circuit,level,name,comment,qq,zz,pbsb,id,*name,part,type,divisor/values,unit,comment\n")
        fh.write("# Ochsner OTE / TEM controller, eBUS slave 15, MF=TEM ID=24849\n"
                 "# reverse engineered and verified on: Ochsner TERRA DX 5 HCUA (direct expansion/water, R407C),\n"
                 "#   application type 15-006 = 8 GMDWplus, controller SW 6.05 HW 3.03, Fachpartner level\n"
                 "# other Ochsner heat pumps with the same controller may expose different blocks/parameters\n")
        w = csv.writer(fh, lineterminator="\n")
        for r in rows:
            w.writerow(r)
    print("%d Zeilen -> %s" % (len(rows), out))


if __name__ == "__main__":
    main()
