#!/usr/bin/env python3
"""Régénère la base intégrée dans index.html depuis Elektron/Tonverk.csv.

    python3 tools/embed.py Tonverk.csv
"""
import csv, json, re, sys, pathlib

def num(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None

def build(path):
    secs, out = [], []
    for r in csv.DictReader(open(path, encoding="utf-8")):
        sec = r.get("section") or "Divers"
        if sec not in secs:
            secs.append(sec)
        p = {"s": secs.index(sec), "n": r["parameter_name"]}
        cc, m, l = num(r.get("cc_msb")), num(r.get("nrpn_msb")), num(r.get("nrpn_lsb"))
        if cc is not None:
            p["c"] = cc
            p["mi"] = num(r.get("cc_min_value")) or 0
            mx = num(r.get("cc_max_value")); p["ma"] = 127 if mx is None else mx
            d = num(r.get("cc_default_value"))
        elif m is not None and l is not None:
            p["m"], p["l"] = m, l
            p["mi"] = num(r.get("nrpn_min_value")) or 0
            mx = num(r.get("nrpn_max_value")); p["ma"] = 16383 if mx is None else mx
            d = num(r.get("nrpn_default_value"))
        else:
            continue
        if d is not None:
            p["d"] = d
        if r.get("orientation") == "centered":
            p["ctr"] = 1
        out.append(p)
    return {"sections": secs, "params": out}

def main(csv_path, html_path="index.html"):
    db = build(csv_path)
    blob = json.dumps(db, separators=(",", ":"), ensure_ascii=False)
    f = pathlib.Path(html_path)
    html = f.read_text(encoding="utf-8")
    pat = re.compile(r'(<script type="application/json" id="paramdb">).*?(</script>)', re.S)
    if not pat.search(html):
        sys.exit("balise #paramdb introuvable dans " + html_path)
    f.write_text(pat.sub(lambda m: m.group(1) + blob + m.group(2), html, count=1), encoding="utf-8")
    print(f"{len(db['params'])} paramètres intégrés dans {html_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: embed.py Tonverk.csv [index.html]")
    main(*sys.argv[1:3])
