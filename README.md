# Clinical NLP Pipeline — MVP

Two-stage pipeline for clinical note processing with configurable checks between stages.

```
data/*.txt
    │
    ▼
pipeline/deid.py          regex + spaCy → redacted text + PII spans
    │
pipeline/deid_check.py    hard check — RED stops pipeline, GREEN continues
    │
    ├── RED  → privacy record written, Stage 2 skipped
    │
    └── GREEN ▼
pipeline/ner.py           HuggingFace NER on redacted text (never sees original)
    │
pipeline/ner_check.py     soft check — flags low confidence + SNOMED lookup
    │
pipeline/snomed.py        SNOMED CT lookup (if enabled in config)
    │
    ▼
outputs/privacy/          🔒 restricted  (original text + PII)
outputs/medical/          ✓  reusable   (redacted text + entities + SNOMED)
outputs/logs.jsonl        audit log     (no raw text)
```

## Setup

```bash
conda create -n clinical-nlp python=3.11 -y
conda activate clinical-nlp
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## Run

```bash
# all notes in data/
python main.py --config config.yaml

# single note
python main.py --config config.yaml --note data/note_001_copd.txt

# research config (lower thresholds)
python main.py --config configs/research.yaml
```

## Project structure

```
main.py                    entrypoint + orchestration
pipeline/
    deid.py                Stage 1: regex + spaCy de-identification
    deid_check.py          hard check after Stage 1 (RED/GREEN)
    ner.py                 Stage 2: HuggingFace clinical NER
    ner_check.py           soft check after Stage 2 (GOOD/WARNING/POOR)
    snomed.py              SNOMED CT lookup
utils/
    config.py              load YAML config
    logging.py             setup + structured audit logging
configs/
    research.yaml          lower thresholds for exploration
config.yaml                default config
data/
    *.txt                  clinical notes (10 synthetic examples)
    known_pii.json         known patient names/IDs for script check
outputs/
    privacy/               🔒 one JSON per note (contains original text)
    medical/               ✓  one JSON per note (safe to share)
    logs.jsonl             structured audit log
notebooks/
    01_evaluation.ipynb    charts: gate results, PII/entity distributions
    02_llm_evaluation.ipynb Claude evaluates deid + NER quality
```

## Config reference

```yaml
deid:
  model: "OpenMed/OpenMed-PII-GTEMed-Base-149M-v1"   # 149M, 54 PII types, real scores
  # swap to OpenMed-PII-ClinicalE5-Large-335M-v1 for higher accuracy

deid_check:
  confidence_threshold: 0.50      # scored entities below this → RED
  confidence: true                 # toggle confidence check
  script: true                     # toggle known_pii.json scan
  # spaCy entities are assigned score=1.0 (deterministic — no beam scoring in standard API)

ner:
  model: "d4data/biomedical-ner-all"
  min_score: 0.30                 # hard floor — entities below this dropped

ner_check:
  review_threshold: 0.60          # entities between min_score and this → review:true

snomed:
  enabled: false                   # set true when SNOMED API is available
  api_url: "https://browser.ihtsdotools.org/snowstorm/snomed-ct/browser/MAIN/concepts"
  timeout_s: 5
```

## Output files

**Privacy record** (`outputs/privacy/<note_id>_privacy.json`) — restricted:
- `original_text`, `redacted_text`, `pii_entities`, `deid_check` result

**Medical record** (`outputs/medical/<note_id>_medical.json`) — reusable:
- `redacted_text`, `entities` (with `review` flag + `snomed` if enabled), `ner_check` result

Both files share the same `record_id` UUID.

## Log format

Console:
```
2026-06-27 10:01:02  INFO      [deid.run]          redacted 5 entity/ies
2026-06-27 10:01:02  WARNING   [deid_check._check_confidence]  3 spaCy entity/ies have no score
2026-06-27 10:01:02  INFO      [deid_check.run]    status=GREEN — all checks passed
2026-06-27 10:01:03  INFO      [ner.run]            extracted 6 entity/ies (min_score=0.30)
```

## Evaluation

After running the pipeline:
```bash
jupyter notebook notebooks/
```
- `01_evaluation.ipynb` — gate results, PII types, entity confidence charts
- `02_llm_evaluation.ipynb` — Claude reviews deid and NER quality (needs `ANTHROPIC_API_KEY`)
