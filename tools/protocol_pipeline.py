# -*- coding: utf-8 -*-
"""Protocol pipeline — turn a procedure spec into a hazard-annotated step checklist.

For a qualified chemist (owner is a PhD chemist): takes a procedure the user supplies
(steps + named reagents + optional target scale), enriches each step with OFFICIAL public
hazard data from PubChem (NIH, keyless PUG REST) — GHS H-codes + molecular weight — and
computes amounts from MW where a target mol/mass is given. Pushes a `protocol` checklist
the user ticks through hands-free on the glasses.

This is a SAFETY + procedure-formatting assistant: it surfaces public safety data and
structures procedures the professional provides/approves. It does not originate routes
for making hazardous or restricted substances. The committable seed is a generic,
harmless textbook prep only.

Usage:
  python tools/protocol_pipeline.py --procedure myprep.json --push
  python tools/protocol_pipeline.py --template --out apps/protocol/seed.json
Procedure spec: {"name":..., "steps":[{"step":..., "reagent"?:..., "mol"?:, "mass_g"?:, "note"?:}]}
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE = os.path.join(ROOT, "apps", "protocol", "example.json")
PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
UA = {"User-Agent": "meta-glass-protocol/1.0 (lab safety companion)"}

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_cache = {}


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


# Ubiquitous lab solvents where PubChem's aggregated GHS is dominated by supplier/mixture
# noise (e.g. water flagged H315) — reporting hazards here erodes trust in the tool. The
# chemist knows these; suppress the aggregate and label them low-hazard.
_BENIGN = {"water", "distilled water", "deionized water", "ice"}


def pubchem(name):
    """Reagent name -> {cid, mw, formula, hazard} from PubChem (cached). Blank on miss."""
    key = name.lower().strip()
    if key in _cache:
        return _cache[key]
    if key in _BENIGN:
        info = {"cid": None, "mw": 18.02 if "water" in key or key == "ice" else None,
                "formula": "H2O" if "water" in key or key == "ice" else "", "hazard": "—"}
        _cache[key] = info
        return info
    info = {"cid": None, "mw": None, "formula": "", "hazard": ""}
    try:
        cids = get_json("%s/compound/name/%s/cids/JSON" % (PUG, urllib.parse.quote(name)))
        cid = cids["IdentifierList"]["CID"][0]
        info["cid"] = cid
        pr = get_json("%s/compound/cid/%d/property/MolecularFormula,MolecularWeight/JSON"
                      % (PUG, cid))["PropertyTable"]["Properties"][0]
        info["mw"] = float(pr.get("MolecularWeight") or 0) or None
        info["formula"] = pr.get("MolecularFormula", "")
        info["hazard"] = ghs_codes(cid)
    except Exception:
        pass
    _cache[key] = info
    return info


def ghs_codes(cid):
    """Pull GHS hazard statements (H-codes) from the PubChem PUG-View safety section."""
    try:
        d = get_json("https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/%d/"
                     "JSON?heading=GHS+Classification" % cid)
    except Exception:
        return ""
    codes = set()
    def walk(o):
        if isinstance(o, dict):
            s = o.get("String", "")
            for m in re.findall(r"\bH\d{3}[Ff]?\b", s):
                codes.add(m)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(d)
    return " ".join(sorted(codes)[:8])


def amount_for(step, mw):
    if mw:
        if step.get("mol") is not None:
            g = float(step["mol"]) * mw
            return "%.3g g / %.3g mol" % (g, float(step["mol"]))
        if step.get("mass_g") is not None:
            mol = float(step["mass_g"]) / mw
            return "%.3g g / %.3g mol" % (float(step["mass_g"]), mol)
    if step.get("mass_g") is not None:
        return "%.3g g" % float(step["mass_g"])
    return ""


def build_items(spec):
    items = []
    for i, s in enumerate(spec.get("steps", []), 1):
        reagent = (s.get("reagent") or "").strip()
        info = pubchem(reagent) if reagent else {"mw": None, "hazard": "", "formula": ""}
        haz = info["hazard"]
        rlabel = reagent + (" (%s)" % info["formula"] if info.get("formula") else "")
        items.append({
            "id": "s_%02d" % i, "n": i, "step": s.get("step", ""),
            "reagent": rlabel if reagent else "",
            "amount": amount_for(s, info.get("mw")),
            "hazard": ("⚠ " + haz) if (haz and haz != "—")
                      else ("low hazard" if haz == "—"
                            else ("no GHS data" if reagent else "")),
            "note": s.get("note", ""),
            "seen": False, "fav": False,
        })
        print("  step %2d %-40s %s" % (i, (s.get("step") or "")[:40],
                                       haz or ("" if not reagent else "(no GHS)")))
    return items


def main(argv):
    out, push, template, proc = "", False, False, ""
    i = 0
    while i < len(argv):
        if argv[i] == "--out" and i + 1 < len(argv):
            out = argv[i + 1]; i += 2
        elif argv[i] == "--procedure" and i + 1 < len(argv):
            proc = argv[i + 1]; i += 2
        elif argv[i] == "--push":
            push = True; i += 1
        elif argv[i] == "--template":
            template = True; i += 1
        elif argv[i] in ("-h", "--help"):
            print(__doc__); return 0
        else:
            i += 1
    if not out and not push:
        print("usage: protocol_pipeline.py [--template | --procedure FILE] [--out FILE] [--push]")
        return 2

    if template or not proc:
        spec = json.load(open(EXAMPLE, encoding="utf-8"))
        print("protocol_pipeline: EXAMPLE procedure (generic, committable)")
    else:
        spec = json.load(open(proc, encoding="utf-8"))
        print("protocol_pipeline: procedure '%s'" % spec.get("name", proc))
    print("protocol_pipeline: enriching with PubChem hazards…")
    items = build_items(spec)
    print("  total: %d step(s)" % len(items))
    if not items:
        print("no steps in the procedure spec"); return 1
    if out:
        tmp = out + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=1)
        os.replace(tmp, out)
        print("wrote %s" % out)
    if push:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import push as pushmod
        return pushmod.main(["protocol", "--replace", "--items", json.dumps(items)])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
