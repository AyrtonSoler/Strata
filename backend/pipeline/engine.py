"""Module B: deterministic address -> applicable rules engine.

Rules come from the extraction pipeline (rules.json). Everything here is plain
code so every answer is reproducible and explainable: which jurisdiction layer a
rule comes from, its status on the query date, and which coverage test decided
the result. When the data lacks the fact a test needs, the answer is "unknown".
"""

import datetime as dt
import re

RESULT_ORDER = {"applies": 0, "superseded": 1, "unknown": 2, "not_yet_effective": 3, "pending": 4}


def parse_date(s: str | None, *, end: bool = False) -> dt.date | None:
    """'2026' -> 2026-01-01 (or 12-31 with end=True); '2026-03' -> 2026-03-01."""
    if not s:
        return None
    m = re.match(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?$", s.strip())
    if not m:
        return None
    y, mo, d = int(m[1]), m[2], m[3]
    if d:
        return dt.date(y, int(mo), int(d))
    if mo:
        return dt.date(y, int(mo), 28 if end else 1)
    return dt.date(y, 12, 31) if end else dt.date(y, 1, 1)


def status_as_of(rule: dict, as_of: dt.date) -> str:
    inst = rule.get("instrument_status", "enacted")
    if inst in ("pending", "failed"):
        return inst
    eff = parse_date(rule.get("effective_date"))
    if eff and eff > as_of:
        # An amendment/annual adjustment: the earlier version of the rule applies.
        return "in_force" if rule.get("prior_version_in_force") else "not_yet_effective"
    return "in_force"


def jurisdiction_stack(addr: dict) -> list[str]:
    """State, county and city layers. The corpus has no county-level rules, but
    the county is resolved and shown so the stack is complete."""
    stack = [addr["jurisdiction_state"]]
    if addr.get("jurisdiction_county"):
        stack.append(f"{addr['jurisdiction_county']}, {addr['jurisdiction_state']}")
    if addr.get("jurisdiction_city"):
        stack.append(addr["jurisdiction_city"])
    return stack


def _units_text(addr: dict) -> str:
    if addr.get("units") is not None:
        return f"{addr['units']} units"
    if addr.get("units_min"):
        return f"at least {addr['units_min']} units ({addr['units_basis']})"
    return "unit count not in data"


def evaluate_coverage(rule: dict, addr: dict, as_of: dt.date) -> tuple[str, list[str], list[dict]]:
    """Return ('covered' | 'not_covered' | 'unknown', reasons, structured checks)."""
    cov = rule.get("coverage") or {}
    units, umin = addr.get("units"), addr.get("units_min")
    year = addr.get("year_built")
    # Upper bound only (e.g. assessor effective year): can prove "old enough", never "too new".
    ymax = addr.get("year_built_max") if year is None else None
    verdicts: list[tuple[str, str, str]] = []

    if cov.get("min_units"):
        n = cov["min_units"]
        if units is not None:
            verdicts.append(("covered" if units >= n else "not_covered", f"needs {n}+ units; building has {units}", "Minimum units"))
        elif umin and umin >= n:
            verdicts.append(("covered", f"needs {n}+ units; building has {_units_text(addr)}", "Minimum units"))
        else:
            verdicts.append(("unknown", f"needs {n}+ units; {_units_text(addr)}", "Minimum units"))

    if cov.get("max_units"):
        n = cov["max_units"]
        if units is not None:
            verdicts.append(("covered" if units <= n else "not_covered", f"covers buildings of at most {n} units; building has {units}", "Maximum units"))
        elif umin and umin > n:
            verdicts.append(("not_covered", f"covers buildings of at most {n} units; building has {_units_text(addr)}", "Maximum units"))
        else:
            verdicts.append(("unknown", f"covers buildings of at most {n} units; {_units_text(addr)}", "Maximum units"))

    basis = cov.get("age_cutoff_basis") or "year_built"
    basis_txt = "certificate of occupancy" if basis == "certificate_of_occupancy" else "construction"
    cutoff = parse_date(cov.get("built_on_or_before"))
    if cutoff:
        if year is None and ymax and ymax < cutoff.year:
            verdicts.append(("covered", f"parcel data shows it was built in or before {ymax}, before the {cutoff} {basis_txt} cutoff", "Built on or before cutoff"))
        elif year is None:
            verdicts.append(("unknown", f"covers buildings with {basis_txt} on or before {cutoff}; year built not in data", "Built on or before cutoff"))
        elif year < cutoff.year:
            verdicts.append(("covered", f"built {year}, before the {cutoff} {basis_txt} cutoff", "Built on or before cutoff"))
        elif year > cutoff.year:
            verdicts.append(("not_covered", f"built {year}, after the {cutoff} {basis_txt} cutoff", "Built on or before cutoff"))
        elif basis == "year_built" and cutoff.month == 12 and cutoff.day == 31:
            verdicts.append(("covered", f"built {year}, within the cutoff year", "Built on or before cutoff"))
        else:
            verdicts.append(("unknown", f"built {year}, the cutoff year; {basis_txt} date ({cutoff}) not in data", "Built on or before cutoff"))

    after = parse_date(cov.get("built_after"))
    if after:
        if year is None and ymax and ymax < after.year:
            verdicts.append(("not_covered", f"parcel data shows it was built in or before {ymax}, not after {after}", "Built after cutoff"))
        elif year is None:
            verdicts.append(("unknown", f"covers buildings with {basis_txt} after {after}; year built not in data", "Built after cutoff"))
        elif year > after.year:
            verdicts.append(("covered", f"built {year}, after {after}", "Built after cutoff"))
        elif year < after.year:
            verdicts.append(("not_covered", f"built {year}, before {after}", "Built after cutoff"))
        else:
            verdicts.append(("unknown", f"built {year}, the cutoff year; exact date not in data", "Built after cutoff"))

    k = cov.get("exclude_if_newer_than_years")
    if k:
        if year is None and ymax and as_of.year - ymax > k:
            verdicts.append(("covered", f"parcel data shows it was built in or before {ymax}, so it is older than the {k}-year new-construction exemption", "New-construction exemption"))
        elif year is None:
            verdicts.append(("unknown", f"excludes housing newer than {k} years; year built not in data", "New-construction exemption"))
        else:
            age = as_of.year - year
            if age > k:
                verdicts.append(("covered", f"built {year} ({age} years old), not within the {k}-year new-construction exemption", "New-construction exemption"))
            elif age < k - 1:
                verdicts.append(("not_covered", f"built {year}, within the {k}-year new-construction exemption", "New-construction exemption"))
            else:
                verdicts.append(("unknown", f"built {year}, at the edge of the {k}-year new-construction exemption", "New-construction exemption"))

    owner_n = cov.get("owner_exemption_max_units")
    if owner_n:
        if units is not None and units <= owner_n:
            verdicts.append(("unknown", f"owner-based exemption possible for buildings of {owner_n} or fewer units; owner type not in data", "Owner-type exemption"))
        elif units is None and not (umin and umin > owner_n):
            verdicts.append(("unknown", f"owner-based exemption possible for {owner_n} or fewer units; {_units_text(addr)}, owner type not in data", "Owner-type exemption"))
        else:
            verdicts.append(("covered", f"owner-based exemption limited to {owner_n} or fewer units cannot apply", "Owner-type exemption"))
    if cov.get("owner_exemption_any_size"):
        verdicts.append(("unknown", "coverage depends on owner type, which is not in the data", "Owner-type exemption"))

    factor = cov.get("other_unknown_factor")
    if factor and re.search(r"subsidi|affordable|deed", factor, re.I) and \
            re.search(r"SUBSD|AFFORD", addr.get("use_description", ""), re.I):
        verdicts.append(("unknown", f"record flags subsidized/affordable housing; {factor}", "Subsidized housing"))

    checks = [{"test": t, "outcome": {"covered": "met", "not_covered": "not_met", "unknown": "unknown"}[v],
               "detail": r[0].upper() + r[1:]} for v, r, t in verdicts]
    if any(v == "not_covered" for v, _, _ in verdicts):
        return "not_covered", [r for v, r, _ in verdicts if v == "not_covered"], checks
    if any(v == "unknown" for v, _, _ in verdicts):
        return "unknown", [r for v, r, _ in verdicts if v == "unknown"], checks
    reasons = [r for _, r, _ in verdicts] or ["covers all residential rentals in this jurisdiction"]
    if not verdicts:
        checks.append({"test": "Coverage", "outcome": "met",
                       "detail": "The rule covers all residential rentals in this jurisdiction"})
    if factor:
        reasons.append(f"caveat: {factor}")
    return "covered", reasons, checks


def lookup(addr: dict, rules: list[dict], as_of: dt.date) -> list[dict]:
    stack = jurisdiction_stack(addr)
    rows = []
    for rule in rules:
        if rule.get("jurisdiction") not in stack:
            continue
        status = status_as_of(rule, as_of)
        if status == "failed":
            continue
        cov, reasons, checks = evaluate_coverage(rule, addr, as_of)
        if cov == "not_covered":
            continue
        layer = "state law" if rule["level"] == "state" else f"{rule['jurisdiction']} ordinance"
        why = "; ".join(reasons)
        why = why[0].upper() + why[1:]
        if status == "pending":
            result = "pending"
            expl = f"Pending {layer}, not law as of {as_of}. Would cover this address if enacted. {why}."
        elif status == "not_yet_effective":
            result = "not_yet_effective"
            expl = f"Enacted {layer}, effective {rule.get('effective_date')} (after {as_of}). {why}."
        else:
            result = "applies" if cov == "covered" else "unknown"
            expl = f"{layer[0].upper() + layer[1:]} in force. {why}."
        rows.append({"team_rule_id": rule["team_rule_id"], "result": result, "explanation": expl,
                     "conflict_flag": bool(rule.get("conflict_flag")), "_rule": rule,
                     "_checks": checks, "_status": status})

    # Supersession: a state rule that yields to local law of the same category.
    for row in rows:
        rule = row["_rule"]
        if rule["level"] != "state" or not (rule.get("coverage") or {}).get("yields_to_local"):
            continue
        if row["result"] not in ("applies", "unknown"):
            continue
        local = [r for r in rows if r["_rule"]["level"] == "city"
                 and r["_rule"]["category"] == rule["category"] and r["result"] in ("applies", "unknown")]
        if any(r["result"] == "applies" for r in local):
            lid = next(r["team_rule_id"] for r in local if r["result"] == "applies")
            row["result"] = "superseded"
            row["explanation"] = (f"Covered by state law, but the local rule {lid} governs here "
                                  f"({rule.get('interaction') or 'state rule yields to stricter local rule'}).")
        elif local:
            row["result"] = "unknown"
            row["explanation"] += " Whether the local rule displaces it depends on facts not in the data."

    # Possible preemption between levels in the same category -> human review.
    for row in rows:
        if row["result"] in ("pending",):
            continue
        same = [r for r in rows if r is not row and r["_rule"]["category"] == row["_rule"]["category"]
                and r["_rule"]["level"] != row["_rule"]["level"] and r["result"] != "pending"]
        if same and (_preempts(row["_rule"]) or any(_preempts(r["_rule"]) for r in same)):
            row["conflict_flag"] = True

    rows.sort(key=lambda r: (r["_rule"]["category"], RESULT_ORDER[r["result"]], r["team_rule_id"]))
    return rows


def _preempts(rule: dict) -> bool:
    return bool(rule.get("conflict_flag")) and not rule.get("open_questions")


def public_rows(rows: list[dict]) -> list[dict]:
    """Rows in the official lookups.json shape (internal audit fields dropped)."""
    return [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
