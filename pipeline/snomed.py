"""SNOMED CT lookup — called from ner_check.py if snomed.enabled in config."""

import json
import logging
import urllib.parse
import urllib.request

log = logging.getLogger("clinical_nlp")


def lookup(term: str, cfg: dict) -> dict | None:
    log.debug("snomed: looking up '%s'", term)
    try:
        url = (cfg["snomed"]["api_url"]
               + "?term=" + urllib.parse.quote(term)
               + "&limit=1&activeFilter=true")
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=cfg["snomed"]["timeout_s"]) as r:
            items = json.loads(r.read()).get("items", [])
        if not items:
            log.warning("snomed: no concept found for '%s'", term)
            return None
        top = items[0]
        log.debug("snomed: '%s' → %s (%s)", term, top["conceptId"], top["fsn"]["term"])
        return {"concept_id": top["conceptId"], "fsn": top["fsn"]["term"]}
    except Exception as exc:
        log.error("snomed: lookup failed for '%s': %s", term, exc)
        return None
