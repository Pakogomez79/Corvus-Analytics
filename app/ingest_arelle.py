"""
Ingest XBRL using Arelle headless. Extract facts, taxonomy/version, context and units.
Currently focuses on SFC taxonomy; mapping to canonical concepts should use CSVs already present.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from arelle import Cntlr, ModelDocument


class ParsedFact(dict):
    concept_qname: str
    value: Any
    decimals: Optional[int]
    unit: Optional[str]
    currency: Optional[str]
    dimensions: Dict[str, Any]


def parse_xbrl(file_path: Path) -> dict:
    controller = Cntlr.Cntlr(logFileName="-")  # envía log a stdout/stderr
    # Arelle espera string/URL; probar file:// y ruta plana
    file_url = file_path.as_uri() if hasattr(file_path, "as_uri") else str(file_path)
    model_xbrl = controller.modelManager.load(file_url)
    if model_xbrl is None or model_xbrl.modelDocument is None:
        # reintentar con ruta plana por si hay problema con file:// en Windows
        model_xbrl = controller.modelManager.load(str(file_path))

    if model_xbrl is None or model_xbrl.modelDocument is None:
        raise ValueError("No se pudo cargar el documento XBRL (modelDocument nulo)")
    
    # Extraer taxonomía desde targetNamespace o desde schemaRefs
    taxonomy = model_xbrl.modelDocument.targetNamespace
    if not taxonomy:
        # Intentar obtener desde los schemaRefs (referencias a esquemas)
        for doc in model_xbrl.urlDocs.values():
            if doc.type == ModelDocument.Type.SCHEMA:
                taxonomy = doc.targetNamespace
                if taxonomy:
                    break
        # Si aún no hay, buscar en los schemaRef links
        if not taxonomy and hasattr(model_xbrl.modelDocument, 'referencesDocument'):
            for ref_doc in model_xbrl.modelDocument.referencesDocument.keys():
                if ref_doc.targetNamespace:
                    taxonomy = ref_doc.targetNamespace
                    break
    
    # Extraer versión - intentar múltiples fuentes
    version = None
    if hasattr(model_xbrl.modelDocument, 'modelVersionIdentifier'):
        version = model_xbrl.modelDocument.modelVersionIdentifier
    
    # Buscar fecha de versión en la URI de la taxonomía
    if not version and taxonomy:
        # Buscar patrones de fecha como 2016-04-01 en la URL de taxonomía
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', taxonomy)
        if date_match:
            version = date_match.group(1)
    
    # Obtener información del schemaRef para mejor descripción de taxonomía
    schema_ref = None
    if hasattr(model_xbrl.modelDocument, 'schemaLocationElements'):
        for elem in model_xbrl.modelDocument.schemaLocationElements:
            href = elem.get('{http://www.w3.org/1999/xlink}href')
            if href:
                schema_ref = href
                break
    
    # Si no encontramos taxonomía, usar el schemaRef como referencia
    if not taxonomy and schema_ref:
        taxonomy = schema_ref
    
    # Extraer nombre corto de la taxonomía desde el schemaRef o namespace
    taxonomy_name = None
    if schema_ref:
        # Extraer el nombre del archivo de entrada del esquema
        match = re.search(r'/([^/]+_entry-point[^/]*\.xsd)', schema_ref)
        if match:
            taxonomy_name = match.group(1).replace('.xsd', '').replace('_entry-point_', ' v')
        else:
            # Intentar extraer algo útil del namespace
            if 'superfinanciera' in (taxonomy or '').lower():
                taxonomy_name = "SFC Colombia IFRS"
    
    # Usar el nombre corto si está disponible
    final_taxonomy = taxonomy_name or taxonomy

    facts: List[ParsedFact] = []
    for f in model_xbrl.factsInInstance:
        if f.isNil:  # skip nil facts
            continue
        val = f.value
        dec = f.decimals
        # Usar comprobaciones explícitas para evitar FutureWarning de elementos XML
        unit = getattr(f.unit, "id", None) if f.unit is not None else None
        currency = None
        if f.unit is not None and f.unit.measures is not None and len(f.unit.measures) > 0 and len(f.unit.measures[0]) > 0:
            currency = f.unit.measures[0][0].localName
        context = f.context
        ctx_start = getattr(context, "startDatetime", None)
        ctx_end = getattr(context, "endDatetime", None) or getattr(context, "instantDatetime", None)
        entity_identifier = None
        if context is not None and getattr(context, "entityIdentifier", None) is not None:
            scheme, ident = context.entityIdentifier
            entity_identifier = {"scheme": scheme, "identifier": ident}
        dims = {}
        if context is not None and getattr(context, "segDimValues", None) is not None:
            for dim, mem in context.segDimValues.items():
                dims[str(dim.qname)] = str(mem.memberQname)
        facts.append(
            {
                "concept_qname": str(f.qname),
                "value": val,
                "decimals": int(dec) if dec is not None else None,
                "unit": unit,
                "currency": currency,
                "dimensions": dims,
                "period_start": ctx_start.date() if ctx_start else None,
                "period_end": ctx_end.date() if ctx_end else None,
                "entity_identifier": entity_identifier,
            }
        )

    return {
        "taxonomy": final_taxonomy,
        "version": version,
        "facts": facts,
    }
