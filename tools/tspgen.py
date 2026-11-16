#!/usr/bin/env python3
"""Convert the generated ebusd CSV (generated/15.24849.csv) to a TypeSpec (.tsp)
file for the current john30/ebusd-configuration repo (src/tem/15.24849.tsp).

Reuses the shared TEM templates (command/parameter1/TEM_P/number types) and emits
one model per message with an explicit @id. Value lists become local enums.
"""
import csv, re, sys, unicodedata

SRC = sys.argv[1] if len(sys.argv) > 1 else "generated/15.24849.csv"
OUT = sys.argv[2] if len(sys.argv) > 2 else "out.tsp"

# ---- helpers ---------------------------------------------------------------
def ident(s):
    """Make a valid TypeSpec identifier from arbitrary text."""
    s = (s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
           .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue").replace("ß", "ss"))
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    if not s:
        s = "x"
    if s[0].isdigit():
        s = "_" + s
    return s

def model_name(raw):
    """CamelCase model name from the ebusd message name (pNN_MMM_text)."""
    base = ident(raw)
    parts = [p for p in base.split("_") if p]
    return "".join(w[:1].upper() + w[1:] for w in parts) or "M"

def id_bytes(pbsb, idhex):
    b = [int(pbsb[0:2], 16), int(pbsb[2:4], 16)]
    b += [int(idhex[i:i+2], 16) for i in range(0, len(idhex), 2)]
    return b

def hexlist(bs):
    return ", ".join("0x%x" % b for b in bs)

# ---- value list (enum) registry -------------------------------------------
enums = {}         # key -> (enum_name, [(member, value)])
enum_by_text = {}  # dedupe identical lists

def enum_for(values, hint):
    """values = '0=a;1=b;...' -> returns enum name, registering it."""
    pairs = []
    for part in values.split(";"):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        k = k.strip()
        try:
            num = int(k, 0)
        except ValueError:
            continue
        pairs.append((ident(v.strip()) or ("v%s" % num), num))
    if not pairs:
        return None
    # dedupe members with same name
    seen = {}
    uniq = []
    for name, num in pairs:
        n = name
        i = 1
        while n in seen and seen[n] != num:
            i += 1
            n = "%s_%d" % (name, i)
        if n in seen:
            continue
        seen[n] = num
        uniq.append((n, num))
    key = tuple(uniq)
    if key in enum_by_text:
        return enum_by_text[key]
    name = "Values_%s" % ident(hint)
    base = name
    i = 1
    while name in enums:
        i += 1
        name = "%s_%d" % (base, i)
    enums[name] = uniq
    enum_by_text[key] = name
    return name

# ---- value field -> TSP property ------------------------------------------
NUMERIC = {"UCH", "SCH", "UIN", "SIN", "UIR", "SIR", "U2B", "S2B",
           "HCD", "BCD", "D1C", "D2B", "UCHB", "BI3", "BI6"}

def value_prop(ftype, div, unit, values, pname="value"):
    """Return (decorator lines, 'name: Type;') for a value field."""
    decos = []
    m = re.match(r"([A-Z0-9]+)(?::(\d+))?$", ftype)
    base = m.group(1) if m else ftype
    length = m.group(2) if m else None
    if values:
        en = enum_for(values, pname)
        if en:
            decos.append("@values(%s)" % en)
    if div and div not in ("", "1"):
        decos.append("@divisor(%s)" % div)
    if unit:
        decos.append('@unit("%s")' % unit)
    tsptype = base
    if base in ("HCD", "BCD") and length:
        tsptype = base + length           # HCD:4 -> HCD4
    elif base == "STR" and length:
        tsptype = "STR"
        decos.append("@maxLength(%s)" % length)
    elif base == "IGN" and length:
        tsptype = "IGN"
        decos.append("@maxLength(%s)" % length)
    return decos, tsptype

# ---- parse CSV -------------------------------------------------------------
rows = []
with open(SRC, encoding="utf-8") as fh:
    rd = csv.reader(fh)
    header = next(rd)
    for r in rd:
        if not r or r[0].startswith("#") or r[0].startswith("*"):
            continue
        rows.append(r)

def fields(r):
    """yield (name, part, type, div, unit, comment) tuples from col 9 on."""
    f = r[9:]
    while len(f) >= 6:
        yield f[0], f[1], f[2], f[3], f[4], f[5]
        f = f[6:]

models = []   # (circuit, cond, decorators[], name, comment, body_lines[])
skipped = []

def add(circuit, cond, decos, nm, comment, body):
    models.append((circuit, cond, decos, nm, comment, body))

for r in rows:
    typ, circuit, level, name, comment = r[0], r[1], r[2], r[3], r[4]
    qq, zz, pbsb, idhex = r[5], r[6], r[7], r[8]
    cond = ""
    mt = re.match(r"\[fp=1\](.*)", typ)
    if mt:
        cond = "fp"
        typ = mt.group(1)
    nicec = comment or name
    flds = list(fields(r))

    # --- normal parameter read (0621): IGN:8 + value, or counter IGN:6 + HCD ---
    if typ.startswith("r") and pbsb == "0621" and len(flds) == 2:
        first, val = flds[0], flds[1]
        prefix = "parameter1" if first[2] == "IGN:8" else "paramc" if first[2] == "IGN:6" else None
        if prefix:
            div = "" if "=" in val[3] else val[3]
            values = val[3] if "=" in val[3] else ""
            decos, tsptype = value_prop(val[2], div, val[4], values, pname=name)
            body = ["  %s: %s;" % (prefix, prefix)]
            body += ["  %s" % d for d in decos]
            body.append("  value: %s;" % tsptype)
            add(circuit, cond, ["@id(%s)" % hexlist(id_bytes(pbsb, idhex))],
                model_name(name), nicec, body)
            continue

    # --- operating-hours counter (0621): IGN:6 + minutes(UCH) + hours(HCD:3) ---
    if (typ.startswith("r") and pbsb == "0621" and len(flds) == 3
            and flds[0][2] == "IGN:6" and flds[2][2].startswith("HCD")):
        body = ["  paramc: paramc;",
                '  @unit("min")', "  minutes: UCH;",
                '  @unit("h")', "  hours: HCD3;"]
        add(circuit, cond, ["@id(%s)" % hexlist(id_bytes(pbsb, idhex))],
            model_name(name), nicec, body)
        continue

    # --- text read (0622): one STR value, possibly chained over 2 ids ---
    if typ.startswith("r") and pbsb == "0622" and len(flds) == 1 and flds[0][2].startswith("STR"):
        ids = idhex.split(";")
        b0 = id_bytes(pbsb, ids[0])
        decolist = ["@id(%s)" % hexlist(b0)]
        if len(ids) > 1:
            extra = ", ".join("#[%s]" % hexlist(id_bytes(pbsb, i)[2:]) for i in ids[1:])
            decolist.append("@chain(0, %s)" % extra)
        decos, tsptype = value_prop(flds[0][2], "", "", "", pname=name)
        body = ["  %s" % d for d in decos] + ["  value: %s;" % tsptype]
        add(circuit, cond, decolist, model_name(name), nicec, body)
        continue

    # --- passive master-master telegrams (0501 request, 0503 module status) ---
    if typ == "u" and pbsb in ("0501", "0503"):
        idtail = id_bytes("0000", idhex)[2:] if idhex else []
        decolist = ["@passive", "@qq(0x%s)" % qq, "@zz(0x%s)" % zz,
                    "@id(0x%02x, 0x%02x%s)" % (int(pbsb[0:2], 16), int(pbsb[2:4], 16),
                     "".join(", 0x%x" % b for b in idtail))]
        body = []
        ign = 0
        for fn, part, ft, fdiv, funit, fcom in flds:
            if ft.startswith("IGN"):
                n = ft.split(":")[1] if ":" in ft else "1"
                body.append("  @maxLength(%s) _ign%d: IGN;" % (n, ign)); ign += 1
                continue
            div = "" if "=" in fdiv else fdiv
            values = fdiv if "=" in fdiv else ""
            decos, tsptype = value_prop(ft, div, funit, values, pname="%s_%s" % (name, fn))
            if fcom:
                body.append("  /** %s */" % fcom)
            body += ["  %s" % d for d in decos]
            body.append("  %s: %s;" % (ident(fn).lower() or "value", tsptype))
        add(circuit, "", decolist, model_name(name) + model_name(circuit), nicec, body)
        continue

    skipped.append((typ, circuit, name, pbsb))

# disambiguate model names that recur across circuits (ebusd dedups on name)
from collections import Counter
_namecount = Counter(m[3] for m in models)
models = [(m[0], m[1], m[2], m[3] + model_name(m[0]) if _namecount[m[3]] > 1 else m[3],
           m[4], m[5]) for m in models]

# ---- emit ------------------------------------------------------------------
def emit():
    out = []
    out.append('import "@ebusd/ebus-typespec";')
    out.append('import "./_templates.tsp";')
    out.append("using Ebus;")
    out.append("using Ebus.Num;")
    out.append("using Ebus.Dtm;")
    out.append("using Ebus.Str;")
    out.append("namespace Tem;")
    out.append("")
    out.append("// Ochsner TERRA DX 5 HCUA (TEM controller), eBUS slave 15, MF=TEM ID=24849, SW 6.05 HW 3.03.")
    out.append("// Reverse engineered via the direct-id scheme (GG,0x80+param,00,0x40+block); the menu-list")
    out.append("// ids are unreliable on this unit. Settings marked with the Fachpartner condition are only")
    out.append("// read while access level 04-043 is Fachpartner/OEM. Writes and the error history (0622")
    out.append("// multi-part) are intentionally omitted here. Other Ochsner/TEM units may differ.")
    out.append("namespace _24849 {")
    out.append("  /** 6-byte parameter prefix for counters (group,value,type,unit,max) */")
    out.append("  model paramc {")
    out.append("    command: command;")
    out.append("    max: maxs;")
    out.append("  }")
    out.append("")
    # enums
    for en, members in enums.items():
        out.append("  enum %s {" % en)
        for nm, num in members:
            out.append("    %s: %d," % (nm, num))
        out.append("  }")
        out.append("")
    # models grouped by circuit into named namespaces
    circuits = []
    for m in models:
        if m[0] not in circuits:
            circuits.append(m[0])
    for circ in circuits:
        out.append("  @zz(0x15)")
        out.append("  namespace %s {" % model_name(circ))
        for c, cond, decos, nm, comment, body in models:
            if c != circ:
                continue
            out.append("    /** %s */" % comment)
            if cond == "fp":
                out.append('    @condition(Anlage.P04043EbeneEinsteller.value, "Fachpartner", "OEM")')
            for d in decos:
                out.append("    %s" % d)
            out.append("    model %s {" % nm)
            out.extend(["  " + b for b in body])
            out.append("    }")
            out.append("")
        out.append("  }")
        out.append("")
    out.append("}")
    return "\n".join(out) + "\n"

open(OUT, "w", encoding="utf-8").write(emit())
print("%d models, %d enums -> %s" % (len(models), len(enums), OUT))
if skipped:
    import collections
    c = collections.Counter(s[0] + " " + s[3] for s in skipped)
    print("skipped %d rows:" % len(skipped), dict(c))
