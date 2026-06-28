"""
Clinical NLP Pipeline — MVP

Usage:
    python main.py --config config.yaml
    python main.py --config configs/research.yaml
    python main.py --config config.yaml --note data/note_001_copd.txt
"""

import argparse
import json
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path

from utils import config as cfg_utils
import logging
from utils import logging as log_utils

log = logging.getLogger("clinical_nlp")

from pipeline import deid, deid_check, ner, ner_check

QUALITY_ICON = {"GOOD": "✓", "WARNING": "⚠", "POOR": "✗"}


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def process(text: str, note_id: str, cfg: dict) -> dict:
    log.info("process: starting note_id=%s", note_id)
    t0 = time.perf_counter()
    record_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # ── Stage 1: deid → deid_check ───────────────────────────────────────────
    redacted, pii = deid.run(text, cfg)
    chk1 = deid_check.run(redacted, pii, cfg)

    write(Path(cfg["paths"]["privacy"]) / f"{note_id}_privacy.json", {
        "record_id":      record_id,
        "note_id":        note_id,
        "schema_version": cfg["schema_version"],
        "processed_at":   now,
        "mode":           cfg["mode"],
        "model":    cfg["deid"]["model"],
        "original_text":  text,       # RESTRICTED
        "redacted_text":  redacted,
        "pii_entities":   pii,
        "deid_check":     chk1,
    })

    log.debug("process: writing privacy record")

    if chk1["status"] == "RED":
        log_utils.write(cfg, {"event": "deid_check_red", "note_id": note_id,
                               "reasons": chk1["reasons"]})
        return {"note_id": note_id,
                "deid_check": "RED", "ner_check": None, "entity_count": 0}

    # ── Stage 2: ner → ner_check ─────────────────────────────────────────────
    log.info("process: deid_check GREEN — proceeding to Stage 2")
    entities = ner.run(redacted, cfg)
    chk2 = ner_check.run(entities, cfg)

    write(Path(cfg["paths"]["medical"]) / f"{note_id}_medical.json", {
        "record_id":      record_id,
        "note_id":        note_id,
        "schema_version": cfg["schema_version"],
        "processed_at":   now,
        "mode":           cfg["mode"],
        "ner_model":      cfg["ner"]["model"],
        "snomed_enabled": cfg["snomed"]["enabled"],
        "redacted_text":  redacted,
        "entities":       entities,
        "ner_check":      chk2,
    })

    ms = round((time.perf_counter() - t0) * 1000, 1)
    log.debug("process: writing medical record")
    log_utils.write(cfg, {
        "event":       "note_processed",
        "note_id":     note_id,
        "deid_check":  chk1["status"],
        "ner_check":   chk2["quality"],
        "pii_count":   len(pii),
        "entity_count":len(entities),
        "runtime_ms":  ms,
        "ner_model":   cfg["ner"]["model"],
    })

    return {"note_id": note_id, "deid_check": chk1["status"],
            "ner_check": chk2["quality"], "entity_count": len(entities)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clinical NLP Pipeline")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--note", default=None, help="Single note to process.")
    args = parser.parse_args()

    cfg = cfg_utils.load(args.config)
    log_utils.setup(cfg["paths"]["logs"])

    if args.note:
        result = process(Path(args.note).read_text(encoding="utf-8"),
                         Path(args.note).stem, cfg)
        print(json.dumps(result, indent=2))

    else:
        notes = sorted(Path(cfg["paths"]["input"]).glob("*.txt"))
        if not notes:
            raise SystemExit(f"No .txt files in {cfg['paths']['input']}")

        print(f"\nMode: {cfg['mode'].upper()}  |  model: {cfg['ner']['model']}"
              f"  |  SNOMED: {cfg['snomed']['enabled']}")
        print("─" * 65)

        for note_path in notes:
            r = process(note_path.read_text(encoding="utf-8"), note_path.stem, cfg)
            c1 = "🟢" if r["deid_check"] == "GREEN" else "🔴"
            c2 = QUALITY_ICON.get(r["ner_check"] or "", " ")
            print(f"  {note_path.stem:<34} {c1} deid  {c2} ner  {r['entity_count']} entities")

        print("─" * 65)
        print(f"Privacy → {cfg['paths']['privacy']}")
        print(f"Medical → {cfg['paths']['medical']}")
