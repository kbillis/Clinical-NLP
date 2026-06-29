"""Soft check after NER. Never blocks. Adds review flags and quality signal."""

import logging

log = logging.getLogger("clinical_nlp")


def run(entities: list[dict], cfg: dict) -> dict:
    threshold = cfg["ner_check"]["review_threshold"]
    warnings = []

    for e in entities:
        e["REVIEW"] = e["score"] < threshold
        if e["REVIEW"]:
            log.debug("ner_check: '%s' flagged for review (score=%.3f)", e["text"], e["score"])

        if cfg["snomed"]["enabled"]:
            log.error("TODO:checking SNOMED. This is not yet implemented, but it is an good feature.")
            pass

    flagged = sum(1 for e in entities if e["REVIEW"])
    total = len(entities)
    ratio = flagged / max(total, 1)
    quality = "POOR" if (total == 0 or ratio > 0.5) else "WARNING" if warnings else "GOOD"

    log.info("ner_check: quality=%s  flagged=%d/%d  warnings=%d",
             quality, flagged, total, len(warnings))

    return {"quality": quality, "warnings": warnings[:5],
            "reviewed_count": flagged, "total_count": total}
