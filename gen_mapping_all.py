import csv
from pathlib import Path
import openpyxl

XLSX_PATH = Path(r"e:/APLICACIONES PROPIAS/Corvus-Analytics/taxonomias.xlsx")
SHEETS = ["210000", "220000", "310000", "320000", "410000", "420000", "510000", "520000"]
OUTPUT_DIR = Path(r"e:/APLICACIONES PROPIAS/Corvus-Analytics")
DEFAULT_TAXONOMY = "SFC"
DEFAULT_VERSION = "2024"

HEADER = [
    "taxonomy",
    "version",
    "role_code",
    "codigo",
    "descripcion",
    "concept_qname",
    "canonical_concept",
    "sign_adjust",
    "nature",
    "priority",
    "notes",
]

def priority_for(desc: str, qname: str) -> str:
    if not desc:
        return "medio"
    if "Abstract" in (qname or ""):
        return "omit"
    if "Total" in desc or "total" in desc.lower():
        return "critico"
    return "medio"


def main() -> None:
    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    for sheet in SHEETS:
        ws = wb[sheet]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        body = rows[1:]  # skip header
        out_rows = []
        for codigo, descripcion, qname in body:
            prio = priority_for(descripcion or "", qname or "")
            canonical = "" if prio != "omit" else "skip"
            out_rows.append({
                "taxonomy": DEFAULT_TAXONOMY,
                "version": DEFAULT_VERSION,
                "role_code": sheet,
                "codigo": codigo,
                "descripcion": descripcion,
                "concept_qname": qname,
                "canonical_concept": canonical,
                "sign_adjust": 1,
                "nature": "",
                "priority": prio,
                "notes": "",
            })
        out_path = OUTPUT_DIR / f"mapping_sfc_{sheet}.csv"
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=HEADER)
            writer.writeheader()
            writer.writerows(out_rows)
        print(f"written {len(out_rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
