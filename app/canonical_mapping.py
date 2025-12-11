from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Optional

ROOT_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT_DIR / "docs"
CANONICAL_GLOB = "mapping_sfc_*.csv"


def _load_canonical_map() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for path in DOCS_DIR.glob(CANONICAL_GLOB):
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    concept = (row.get("concept_qname") or "").strip()
                    canonical = (row.get("canonical_concept") or "").strip()
                    if not concept or not canonical or canonical.lower() == "skip":
                        continue
                    if concept not in mapping:
                        mapping[concept] = canonical
        except FileNotFoundError:  # pragma: no cover
            continue
    return mapping


CANONICAL_MAP = _load_canonical_map()


def resolve_canonical_concept(concept_qname: Optional[str]) -> Optional[str]:
    if not concept_qname:
        return None
    return CANONICAL_MAP.get(concept_qname.strip())
