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


class FinancialStatementCreate(BaseModel):
    code: str
    name: str
    type: str


class FinancialStatementResponse(BaseModel):
    id: int
    code: str
    name: str
    type: str

    class Config:
        from_attributes = True


class CanonicalLineCreate(BaseModel):
    code: str
    name: str
    statement_id: int
    parent_id: Optional[int] = None
    order: Optional[int] = None
    metadata: Optional[dict] = None


class CanonicalLineResponse(BaseModel):
    id: int
    code: str
    name: str
    statement_id: int
    parent_id: Optional[int]
    order: Optional[int]
    metadata: Optional[dict]

    class Config:
        from_attributes = True


class CanonicalLineTree(BaseModel):
    id: int
    code: str
    name: str
    order: Optional[int]
    children: List["CanonicalLineTree"] = []

    class Config:
        from_attributes = True

# Forward reference update
CanonicalLineTree.update_forward_refs()


class MoveLineRequest(BaseModel):
    new_parent_id: Optional[int] = None
    new_order: int
