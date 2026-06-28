"""Soft check after NER. Never blocks. Adds review flags and quality signal."""

import logging
from pipeline import snomed

log = logging.getLogger("clinical_nlp")


def run(entities: list[dict], cfg: dict) -> dict:
    threshold = cfg["ner_check"]["review_threshold"]
    warnings = []

    for e in entities:
        e["review"] = e["score"] < threshold
        if e["review"]:
            log.debug("ner_check: '%s' flagged for review (score=%.3f)", e["text"], e["score"])

        if cfg["snomed"]["enabled"]:
            e["snomed"] = snomed.lookup(e["text"], cfg)
            if e["snomed"] is None:
                log.warning("ner_check: no SNOMED concept found for '%s'", e["text"])
                warnings.append(f"no SNOMED concept for '{e['text']}'")
            else:
                log.debug("ner_check: SNOMED resolved '%s' → %s",
                          e["text"], e["snomed"]["concept_id"])

    flagged = sum(1 for e in entities if e["review"])
    total = len(entities)
    ratio = flagged / max(total, 1)
    quality = "POOR" if (total == 0 or ratio > 0.5) else "WARNING" if warnings else "GOOD"

    log.info("ner_check: quality=%s  flagged=%d/%d  warnings=%d",
             quality, flagged, total, len(warnings))

    return {"quality": quality, "warnings": warnings[:5],
            "reviewed_count": flagged, "total_count": total}
