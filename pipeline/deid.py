"""
pipeline/deid.py

Stage 1 — run OpenMed model, store results as a list of dicts.
"""

import logging
from transformers import pipeline

log = logging.getLogger("clinical_nlp")
_pipe = None


def run(text: str, cfg: dict) -> tuple[str, list[dict]]:
    global _pipe
    model = cfg["deid"]["model"]

    if _pipe is None:
        log.info("loading deid model: %s", model)
        _pipe = pipeline("token-classification", model=model, aggregation_strategy="simple")

    entities = []
    for item in _pipe(text):
        start, end = int(item["start"]), int(item["end"])
        entities.append({
            "text":   text[start:end],
            "label":  item.get("entity_group", "PII"),
            "start":  start,
            "end":    end,
            "score":  round(float(item["score"]), 3),
        })

    # redact right-to-left
    redacted = text
    for e in sorted(entities, key=lambda x: x["start"], reverse=True):
        redacted = redacted[:e["start"]] + f"[{e['label']}]" + redacted[e["end"]:]

    log.info("found %d PII entities", len(entities))
    return redacted, entities