#!/usr/bin/env python3
"""Read-only scanner for TEM controllers (Ochsner) via ebusd 'hex' command.

Sends 0621 read requests (ZZ 06 21 04 <b1> <b2> <b3> <b4>) and logs responses.
Runs inside the ebusd container, talking to ebusd on localhost:8888.

Usage:
  temscan.py blocks  OUT.jsonl            # discover function blocks
  temscan.py lists   IN.jsonl OUT.jsonl   # sweep b2 for every (b1,block) hit
  temscan.py direct  OUT.jsonl NGROUPS BLOCK...  # GG-PPP for GG < NGROUPS (hex)
  temscan.py ids     OUT.jsonl ID...      # query explicit ids (8 hex chars)
"""
import json, os, socket, sys, time

ZZ = os.environ.get("ZZ", "15")
DELAY = float(os.environ.get("DELAY", "0.05"))
INVALID = "ff9f"


class Ebusd:
    def __init__(self, host="127.0.0.1", port=8888):
        self.addr = (host, port)
        self.connect()

    def connect(self):
        self.s = socket.create_connection(self.addr, timeout=10)
        self.f = self.s.makefile("rw", newline="\n")

    def cmd(self, line):
        for attempt in range(3):
            try:
                self.f.write(line + "\n")
                self.f.flush()
                out = []
                while True:
                    l = self.f.readline()
                    if l == "":
                        raise ConnectionError("closed")
                    l = l.rstrip("\r\n")
                    if l == "":
                        break
                    out.append(l)
                return "\n".join(out)
            except (OSError, ConnectionError):
                time.sleep(2)
                self.connect()
        return "ERR: connection"


def done_ids(path):
    seen = set()
    if os.path.exists(path):
        with open(path) as fh:
            for l in fh:
                try:
                    seen.add(json.loads(l)["id"])
                except Exception:
                    pass
    return seen


def query(eb, ident):
    r = eb.cmd("hex %s062104%s" % (ZZ, ident))
    time.sleep(DELAY)
    return r


def run(eb, ids, out, stop_after_miss=None):
    """Query ids; if stop_after_miss is set, ids is a list of groups (lists)
    and each group is aborted after that many consecutive misses."""
    seen = done_ids(out)
    with open(out, "a") as fh:
        groups = ids if stop_after_miss else [ids]
        for grp in groups:
            miss = 0
            for ident in grp:
                if ident in seen:
                    continue
                r = query(eb, ident)
                ok = not r.startswith("ERR") and r[2:6] != INVALID
                fh.write(json.dumps({"id": ident, "r": r, "ok": ok, "t": int(time.time())}) + "\n")
                fh.flush()
                if ok:
                    print(ident, r, flush=True)
                    miss = 0
                else:
                    miss += 1
                    if stop_after_miss and miss >= stop_after_miss:
                        break


def main():
    mode = sys.argv[1]
    eb = Ebusd()
    if mode == "blocks":
        out = sys.argv[2]
        ids = ["0080%04x" % b for b in range(0, 0x100)]
        ids += ["%02x80%04x" % (b1, b) for b1 in range(0x60, 0x80) for b in range(0, 0x80, 2)]
        run(eb, ids, out)
    elif mode == "lists":
        src, out = sys.argv[2], sys.argv[3]
        hits = sorted({j["id"] for j in map(json.loads, open(src)) if j["ok"]})
        groups = []
        for h in hits:
            b1, blk = h[0:2], h[4:8]
            if int(b1, 16) >= 0x60:
                groups.append(["%s%02x%s" % (b1, b2, blk) for b2 in range(0x80, 0x100)])
        run(eb, groups, out, stop_after_miss=12)
    elif mode == "direct":
        # direct access by parameter number GG-PPP: <GG> <80+PPP> 00 <40+block>
        out, groups = sys.argv[2], int(sys.argv[3], 16)
        for blk in sys.argv[4:]:
            for g in range(groups):
                # log current access level 04-043 alongside the results
                with open(out + ".level", "a") as fh:
                    fh.write("%d %s %02x %s\n" % (time.time(), blk, g, query(eb, "04ab0040")))
                ids = ["%02x%02x00%02x" % (g, 0x80 + p, 0x40 + int(blk, 16)) for p in range(0x80)]
                run(eb, ids, out)
    elif mode == "ids":
        out = sys.argv[2]
        run(eb, sys.argv[3:], out)


if __name__ == "__main__":
    main()
