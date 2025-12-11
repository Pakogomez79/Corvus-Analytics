import csv
from pathlib import Path
import openpyxl

XLSX_PATH = Path(r"e:/APLICACIONES PROPIAS/Corvus-Analytics/taxonomias.xlsx")
SHEET = "220000"
OUTPUT_PATH = Path(r"e:/APLICACIONES PROPIAS/Corvus-Analytics/mapping_sfc_220000.csv")

MAPPING = {
    "ifrs_AssetsAbstract": "skip",
    "ifrs_CashAndCashEquivalents": "efectivo",
    "co-sfc-core_Inversiones": "inversiones",
    "ifrs_OtherFinancialAssets": "otros_activos_financieros",
    "co-sfc-core_CarteraCreditoOperacionesLeasingFinanciero": "cartera_credito_leasing",
    "ifrs_TradeAndOtherReceivables": "cuentas_cobrar",
    "co-sfc-core_CuentasCobrarPartesRelacionadasAsociadasCorrientes": "cxc_relacionadas",
    "co-sfc-core_ReservasTecnicasParteReaseguradores": "reservas_tecnicas_reaseguradores",
    "ifrs_CurrentTaxAssets": "impuestos_corrientes_activo",
    "ifrs_DeferredTaxAssets": "impuestos_diferidos_activo",
    "ifrs_OtherNonfinancialAssets": "otros_activos_no_financieros",
    "ifrs_NoncurrentAssetsOrDisposalGroupsClassifiedAsHeldForSaleOrAsHeldForDistributionToOwners": "activos_mantenidos_venta",
    "ifrs_InvestmentProperty": "propiedad_inversion",
    "ifrs_PropertyPlantAndEquipment": "propiedad_planta_equipo",
    "ifrs_InventoriesTotal": "inventarios",
    "ifrs_BiologicalAssets": "activos_biologicos",
    "ifrs_Goodwill": "goodwill",
    "ifrs_IntangibleAssetsOtherThanGoodwill": "intangibles_sin_goodwill",
    "ifrs_InvestmentAccountedForUsingEquityMethod": "inversiones_metodo_participacion",
    "ifrs_InvestmentsInSubsidiariesJointVenturesAndAssociates": "inversiones_subsidiarias_asociadas",
    "ifrs_Assets": "activos_totales",
    "ifrs_EquityAndLiabilitiesAbstract": "skip",
    "ifrs_LiabilitiesAbstract": "skip",
    "co-sfc-core_DepositosExigibilidades": "depositos_exigibilidades",
    "ifrs_OtherFinancialLiabilities": "otros_pasivos_financieros",
    "co-sfc-core_ReservasTecnicas": "reservas_tecnicas",
    "ifrs_ProvisionsForEmployeeBenefits": "provisiones_beneficios_empleados",
    "ifrs_OtherProvisions": "otras_provisiones",
    "ifrs_TradeAndOtherPayables": "cuentas_por_pagar",
    "co-sfc-core_CuentasPagarEntidadesRelacionadas": "cuentas_pagar_relacionadas",
    "ifrs_CurrentTaxLiabilities": "impuestos_corrientes_pasivo",
    "co-sfc-core_TitulosEmitidos": "deuda_emitida",
    "ifrs_OtherNonfinancialLiabilities": "otros_pasivos_no_financieros",
    "ifrs_LiabilitiesIncludedInDisposalGroupsClassifiedAsHeldForSale": "pasivos_mantenidos_venta",
    "ifrs_DeferredTaxLiabilities": "impuestos_diferidos_pasivo",
    "ifrs_Liabilities": "pasivos_totales",
    "ifrs_EquityAbstract": "skip",
    "ifrs_IssuedCapital": "capital_emitido",
    "co-sfc-core_CapitalAsignado": "capital_asignado",
    "ifrs_TreasuryShares": "acciones_propias",
    "co-sfc-core_InversionSuplementariaCapitalAsignado": "inversion_suplementaria_capital",
    "ifrs_SharePremium": "prima_emision",
    "co-sfc-core_ResultadoEjercicio": "utilidad_ejercicio",
    "ifrs_RetainedEarnings": "ganancias_acumuladas",
    "ifrs_OtherEquityInterest": "otras_participaciones_patrimonio",
    "co-sfc-core_Reservas": "reservas_patrimonio",
    "ifrs_EquityAttributableToOwnersOfParent": "patrimonio_controladora",
    "ifrs_NoncontrollingInterests": "participaciones_no_controladoras",
    "ifrs_Equity": "patrimonio_total",
    "ifrs_EquityAndLiabilities": "pasivo_patrimonio_total",
}

ASSETS = {
    "efectivo",
    "inversiones",
    "otros_activos_financieros",
    "cartera_credito_leasing",
    "cuentas_cobrar",
    "cxc_relacionadas",
    "reservas_tecnicas_reaseguradores",
    "impuestos_corrientes_activo",
    "impuestos_diferidos_activo",
    "otros_activos_no_financieros",
    "activos_mantenidos_venta",
    "propiedad_inversion",
    "propiedad_planta_equipo",
    "inventarios",
    "activos_biologicos",
    "goodwill",
    "intangibles_sin_goodwill",
    "inversiones_metodo_participacion",
    "inversiones_subsidiarias_asociadas",
    "activos_totales",
}

LIABS_EQUITY = {
    "depositos_exigibilidades",
    "otros_pasivos_financieros",
    "reservas_tecnicas",
    "provisiones_beneficios_empleados",
    "otras_provisiones",
    "cuentas_por_pagar",
    "cuentas_pagar_relacionadas",
    "impuestos_corrientes_pasivo",
    "deuda_emitida",
    "otros_pasivos_no_financieros",
    "pasivos_mantenidos_venta",
    "impuestos_diferidos_pasivo",
    "pasivos_totales",
    "capital_emitido",
    "capital_asignado",
    "acciones_propias",
    "inversion_suplementaria_capital",
    "prima_emision",
    "utilidad_ejercicio",
    "ganancias_acumuladas",
    "otras_participaciones_patrimonio",
    "reservas_patrimonio",
    "patrimonio_controladora",
    "participaciones_no_controladoras",
    "patrimonio_total",
    "pasivo_patrimonio_total",
}

CRITICOS = {
    "activos_totales",
    "pasivos_totales",
    "patrimonio_total",
    "pasivo_patrimonio_total",
    "efectivo",
    "cuentas_cobrar",
    "cartera_credito_leasing",
    "inventarios",
    "deuda_emitida",
}

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

def main() -> None:
    ws = openpyxl.load_workbook(XLSX_PATH, data_only=True)[SHEET]
    rows = list(ws.iter_rows(values_only=True))[1:]  # skip header

    output_rows = []
    for codigo, descripcion, qname in rows:
        canonical = MAPPING.get(qname, "")
        if canonical == "skip":
            priority = "omit"
            nature = ""
        else:
            nature = "deudora" if canonical in ASSETS else "acreedora" if canonical in LIABS_EQUITY else ""
            priority = "critico" if canonical in CRITICOS else ("alto" if canonical else "medio")
        sign_adjust = -1 if canonical == "acciones_propias" else 1
        output_rows.append({
            "taxonomy": "SFC",
            "version": "2024",
            "role_code": SHEET,
            "codigo": codigo,
            "descripcion": descripcion,
            "concept_qname": qname,
            "canonical_concept": canonical,
            "sign_adjust": sign_adjust,
            "nature": nature,
            "priority": priority,
            "notes": "",
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"written {len(output_rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
