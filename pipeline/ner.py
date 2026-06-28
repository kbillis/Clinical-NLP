"""Stage 2 — clinical NER on redacted text. Never sees original text."""

import logging
from transformers import pipeline

log = logging.getLogger("clinical_nlp")

LABEL_MAP = {
    "CHEMICAL": "MEDICATION", "PROBLEM": "DISEASE",
    "TREATMENT": "MEDICATION", "TEST": "LAB_VALUE",
}

_pipe = None


def run(redacted_text: str, cfg: dict) -> list[dict]:
    global _pipe
    if _pipe is None:
        log.info("ner: loading model: %s", cfg["ner"]["model"])
        _pipe = pipeline("ner", model=cfg["ner"]["model"], aggregation_strategy="simple")
        log.info("ner: model loaded")

    log.debug("ner: running inference on %d chars", len(redacted_text))
    results = [
        {
            "text":  item["word"].strip("##Ġ▁ "),
            "label": LABEL_MAP.get(item["entity_group"].upper(), item["entity_group"]),
            "start": item["start"],
            "end":   item["end"],
            "score": round(float(item["score"]), 3),
        }
        for item in _pipe(redacted_text)
        if float(item["score"]) >= cfg["ner"]["min_score"]
    ]

    log.info("ner: extracted %d entity/ies (min_score=%.2f)", len(results), cfg["ner"]["min_score"])
    return results
