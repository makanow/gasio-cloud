from __future__ import annotations

# v2: minimal master set for Hokkaido representative case.
MASTERS = {
    '北海道': {
        'yield_m3_per_kg': 0.476,
        'labor_yen_per_person_year': 5683000,
        'persons_per_location_pe': 0.0031,
        'repair_rate': 0.03,
        'expense_rate': 0.15,
        'land_tax_rate': 0.017,
        'asset_tax_rate': 0.014,
        'reduction_factor': 0.46,
        'remuneration_rate': 0.0272,
        'self_capital_ratio': 0.35,
        'corp_tax_coeff': 0.2965,
        'local_corp_tax_rate': 0.103,
        'inhabitant_tax_rate': 0.07,
        'business_tax_rate': 0.009081735620585266,
    }
}

def get_masters(pref_name: str) -> dict:
    if pref_name not in MASTERS:
        raise KeyError(f'Unsupported prefecture in v2: {pref_name}. (v3+ will support all prefectures)')
    return MASTERS[pref_name]
