"""Deterministic grader for AuditBench. No LLM is used to judge anything.

A response is graded on two independent checks:
  flaw  (50 pts): the "flaw" label exactly matches the key (after lowercasing / underscore normalisation)
  value (50 pts): "corrected_value" is within the task's absolute tolerance of the key
A task is PASSED only if both checks are right.
"""
import json
import re

POINTS_FLAW = 50
POINTS_VALUE = 50


def _candidates(text):
    """Yield every JSON object found in text that contains a 'flaw' key, in order."""
    dec = json.JSONDecoder()
    out = []
    for m in re.finditer(r"\{", text or ""):
        try:
            obj, _ = dec.raw_decode(text[m.start():])
        except ValueError:
            continue
        if isinstance(obj, dict) and "flaw" in obj:
            out.append(obj)
    return out


def _norm(flaw):
    return re.sub(r"[\s\-]+", "_", flaw.strip().lower()) if isinstance(flaw, str) else None


def parse_response(text):
    """Return (flaw, value, parse_ok). The LAST JSON object with a 'flaw' key wins.

    Fallback: if no valid JSON object exists (e.g. the model forgot a quote inside "reasoning"), read the
    "flaw" and "corrected_value" fields directly with a strict key:value pattern. This avoids false fails
    on answers whose two graded fields are unambiguous; the fallback never guesses from free prose.
    """
    cands = _candidates(text)
    if cands:
        obj = cands[-1]
        return _norm(obj.get("flaw")), _to_number(obj.get("corrected_value")), True
    fl = re.findall(r'"flaw"\s*:\s*"([^"]{1,40})"', text or "")
    cv = re.findall(r'"corrected_value"\s*:\s*"?\s*(-?[0-9][0-9,]*(?:\.[0-9]+)?)', text or "")
    if fl and cv:
        return _norm(fl[-1]), _to_number(cv[-1]), True
    return None, None, False


def _to_number(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(",", "").replace("%", "").replace("$", "").replace("€", "")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def grade(task, text):
    key = task["key"]
    flaw, value, ok = parse_response(text)
    flaw_ok = ok and flaw == key["flaw"]
    value_ok = ok and value is not None and abs(value - key["value"]) <= key["tol"] + 1e-9
    score = (POINTS_FLAW if flaw_ok else 0) + (POINTS_VALUE if value_ok else 0)
    return {
        "parse_ok": ok,
        "flaw_pred": flaw,
        "value_pred": value,
        "flaw_ok": bool(flaw_ok),
        "value_ok": bool(value_ok),
        "passed": bool(flaw_ok and value_ok),
        "score": score,
        "false_flag": bool(ok and key["flaw"] == "none" and flaw not in (None, "none")),
        "missed_flaw": bool(ok and key["flaw"] != "none" and flaw == "none"),
    }
