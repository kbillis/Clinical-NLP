"""
pipeline/deid.py

Stage 1 — de-identification.

Two-layer approach:
  1. OpenMed HuggingFace model — clinical PII token classifier, returns real scores
  2. Regex fallback — catches structured PII the model may miss (MRN, SSN patterns)

Using OpenMed/OpenMed-PII-GTEMed-Base-149M-v1:
  - 149M params, runs on CPU
  - 54 PII entity types, HIPAA/GDPR aligned
  - Returns per-entity confidence scores → deid_check works properly
"""

import logging
import re
from transformers import pipeline

log = logging.getLogger("clinical_nlp")

# Regex for structured PII the model may miss
REGEX_PATTERNS = {
    "MRN": re.compile(r"\bMRN[:\s#]*\d{4,10}\b", re.IGNORECASE),
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}

_pipe = None


def _get_pipe(model: str):
    global _pipe
    if _pipe is None:
        log.info("loading deid model '%s'", model)
        _pipe = pipeline("token-classification", model=model,
                         aggregation_strategy="simple")
        log.info("deid model loaded")
    return _pipe


def run(text: str, cfg: dict) -> tuple[str, list[dict]]:
    log.debug("starting — input length %d chars", len(text))
    entities = []

    # ── Layer 1: OpenMed model ────────────────────────────────────────────────
    model = cfg["deid"]["model"]
    for item in _get_pipe(model)(text):
        score = round(float(item["score"]), 3)
        entities.append({
            "text":   item["word"].strip("##Ġ▁ "),
            "label":  item["entity_group"],
            "start":  item["start"],
            "end":    item["end"],
            "method": "openmed",
            "score":  score,
        })
    log.debug("openmed: %d entity/ies detected", len(entities))

    # ── Layer 2: regex fallback ───────────────────────────────────────────────
    for label, pattern in REGEX_PATTERNS.items():
        for m in pattern.finditer(text):
            entities.append({
                "text":   m.group(),
                "label":  label,
                "start":  m.start(),
                "end":    m.end(),
                "method": "regex",
                "score":  1.0,
            })
            log.debug("regex: found %s '%s'", label, m.group())

    # merge overlapping spans, sorted by start
    merged, entities = [], sorted(entities, key=lambda e: e["start"])
    for e in entities:
        if merged and e["start"] <= merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], e["end"])
        else:
            merged.append(e)

    # redact right-to-left so offsets stay valid
    redacted = text
    for e in sorted(merged, key=lambda x: x["start"], reverse=True):
        e["text"] = text[e["start"]:e["end"]]
        redacted = redacted[:e["start"]] + f"[{e['label']}]" + redacted[e["end"]:]

    log.info("redacted %d entity/ies (model=%s)", len(merged), model)
    return redacted, merged
