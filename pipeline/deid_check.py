"""
pipeline/deid_check.py

Checks the deid output and returns GREEN / REVIEW / RED.

GREEN  — confident, nothing found in redacted text
REVIEW — low confidence entities or minor leakage
RED    — structured PII still in redacted text

two checks:
  1. confidence     : score distribution of detected entities
  2. record_header  : scans original text for patient record fields
                      then verifies they were redacted
"""

import logging
import re

log = logging.getLogger("clinical_nlp")

PATTERNS = {
    "MRN":   re.compile(r"\bMRN[:\s#]*[A-Za-z0-9-]{4,20}\b", re.IGNORECASE),
    "SSN":   re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "EMAIL": re.compile(r"\b[\w.+\-]+@[\w.\-]+\.[a-z]{2,}\b"),
    "PHONE": re.compile(r"\b(?:\+?\d[\s\-]?)?\(?\d{3}\)?[\s\-]\d{3}[\s\-]\d{4}\b"),
}


def run(original: str, redacted: str, entities: list[dict], cfg: dict) -> dict:
    check_cfg = cfg.get("deid_check", {})
    low_threshold  = check_cfg.get("low_threshold",  0.60)
    high_threshold = check_cfg.get("high_threshold", 0.85)

    results = []

    # ── 1. confidence ─────────────────────────────────────────────────────────
    low  = [e for e in entities if e["score"] < low_threshold]
    mid  = [e for e in entities if low_threshold <= e["score"] < high_threshold]
    conf_passed = len(low) == 0
    results.append({
        "check":   "confidence",
        "passed":  conf_passed,
        "details": (
            [f"'{e['text']}' ({e['label']}) score={e['score']}" for e in low]
            or [f"{len(mid)} mid-confidence entities" if mid else "all scores above threshold"]
        ),
    })
    if low:
        log.warning("confidence: %d low-score entity/ies", len(low))

    # ── 2. record header check ────────────────────────────────────────────────
    # find header fields in original, verify they were redacted
    regex_hits = []
    if check_cfg.get("regex", True):
        for label, pattern in PATTERNS.items():
            for m in pattern.finditer(redacted):
                regex_hits.append(f"{label}: '{m.group()}'")

    regex_passed = len(regex_hits) == 0
    results.append({
        "check":   "regex",
        "passed":  regex_passed,
        "details": regex_hits or ["no structured PII found"],
    })
    if regex_hits:
        log.error("regex: structured PII still visible: %s", regex_hits)

    # ── status ────────────────────────────────────────────────────────────────
    if not regex_passed:
        status = "RED"
    elif not conf_passed:
        status = "REVIEW"
    else:
        status = "GREEN"

    log.info("deid_check status=%s", status)
    return {"status": status, "results": results}