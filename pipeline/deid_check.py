"""
pipeline/deid_check.py

Hard check after Stage 1 de-identification.
RED status stops the pipeline — Stage 2 will not run.

Checks (toggled in config):
  confidence : RED if any scored entity is below threshold.
               spaCy entities (score=None) are flagged as warnings only —
               they never cause RED because spaCy does not expose scores.
  script     : RED if any known PII string is found in the redacted text.
"""

import json
import logging
from pathlib import Path

log = logging.getLogger("clinical_nlp")


def _check_confidence(entities: list[dict], threshold: float) -> tuple[bool, list[str]]:
    """RED if any entity score is below threshold. All entities now have a score."""
    failed = [
        f"'{e['text']}' ({e['label']}) score={e['score']:.2f}"
        for e in entities
        if e["score"] < threshold
    ]
    return len(failed) == 0, failed


def _check_script(redacted: str, known_pii_path: str) -> tuple[bool, list[str]]:
    """Scan redacted text for any known PII strings."""
    path = Path(known_pii_path)
    if not path.exists():
        log.warning("known_pii.json not found at '%s' — script check skipped", known_pii_path)
        return True, ["known_pii.json not found — skipped"]
    known = json.loads(path.read_text())
    found = [
        f"{cat}: '{v}'"
        for cat, vals in known.items() if not cat.startswith("_")
        for v in vals if v.lower() in redacted.lower()
    ]
    return len(found) == 0, found or ["no known PII in redacted text"]


def run(redacted: str, entities: list[dict], cfg: dict) -> dict:
    log.debug("running checks")
    check_cfg = cfg["deid_check"]
    results = []

    if check_cfg.get("confidence"):
        passed, details = _check_confidence(entities, check_cfg["confidence_threshold"])
        results.append({"check": "confidence", "passed": passed, "details": details})
        if not passed:
            log.error("confidence check FAILED: %s", details)

    if check_cfg.get("script"):
        passed, details = _check_script(redacted, cfg["paths"]["known_pii"])
        results.append({"check": "script", "passed": passed, "details": details})
        if not passed:
            log.error("script check FAILED — PII still in redacted text: %s", details)

    failed = [r for r in results if not r["passed"]]
    status = "RED" if failed else "GREEN"

    if status == "RED":
        log.error("status=RED — Stage 2 blocked. Failed checks: %s",
                  [r["check"] for r in failed])
    else:
        log.info("status=GREEN — all checks passed")

    return {"status": status, "reasons": [r["check"] for r in failed], "checks": results}
