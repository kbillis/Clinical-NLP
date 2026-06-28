"""
utils/logging.py

Structured audit logging for the clinical NLP pipeline.
Never logs raw text or PII.

Usage in any module:
    import logging
    log = logging.getLogger("clinical_nlp")
    log.info("message")
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

_configured = False


def setup(log_path: str) -> None:
    """Call once at startup from main.py."""
    global _configured
    if _configured:
        return

    Path(log_path).parent.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s  %(levelname)-8s  [%(module)s.%(funcName)s]  %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter("%(message)s"))  # JSONL — no prefix

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    logger = logging.getLogger("clinical_nlp")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    _configured = True
    logger.info("logging ready — file: %s", log_path)


def write(cfg: dict, record: dict) -> None:
    """Write a structured audit event to the JSONL log file (no PII)."""
    record["timestamp"] = datetime.now(timezone.utc).isoformat()
    record["mode"] = cfg["mode"]
    p = Path(cfg["paths"]["logs"])
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(record) + "\n")
