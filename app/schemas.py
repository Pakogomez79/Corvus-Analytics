from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class FactCreate(BaseModel):
    concept_qname: str
    canonical_concept: Optional[str] = None
    value: Optional[float] = None
    decimals: Optional[int] = None
    unit: Optional[str] = None
    currency: Optional[str] = None
    dimensions: Optional[dict] = None


class FileCreate(BaseModel):
    filename: str
    taxonomy: Optional[str] = None
    version: Optional[str] = None
    currency: Optional[str] = None
    entity_name: Optional[str] = None
    entity_nit: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    facts: List[FactCreate] = []


class FileResponse(BaseModel):
    id: int
    filename: str
    taxonomy: Optional[str]
    version: Optional[str]
    currency: Optional[str]

    class Config:
        from_attributes = True
