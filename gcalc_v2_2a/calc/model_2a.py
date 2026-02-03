from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple
import pandas as pd

from .utils import excel_round, nz
from .trace import Trace

@dataclass
class Form2Table1:
    rows: pd.DataFrame
    sales_m3: float
    unit_cost: float


def compute_2a(entry, masters: dict) -> Tuple[Form2Table1, Trace, Dict[str, float]]:
    tr = Trace()

    permit_locations = nz(entry.basic.get('permit_locations'))
    raw_unit_price = nz(entry.basic.get('raw_unit_price'))

    # A: annual sales
    sales_m3 = float(entry.sales['年間販売量'].fillna(0).sum())
    tr.add(key='A', title='ガスの販売量（年間）', formula='A = Σ(需要種別 年間販売量)',
           inputs={'sales': entry.sales[['需要種別','年間販売量']].to_dict('records')}, value=sales_m3, unit='㎥/年')

    # C: raw material cost
    yield_m3_per_kg = nz(masters.get('yield_m3_per_kg'))
    raw_qty = sales_m3 / yield_m3_per_kg if yield_m3_per_kg else 0.0
    raw_cost = excel_round(raw_qty * raw_unit_price, 0)
    tr.add(key='C', title='原料費', formula='C = ROUND((A / 産気率) × 原料購入単価, 0)',
           inputs={'A': sales_m3, '産気率(m3/kg)': yield_m3_per_kg, '原料購入単価(円/kg)': raw_unit_price}, value=raw_cost, unit='円')

    # D: labor cost
    persons_per_loc = nz(masters.get('persons_per_location_pe'))
    persons = persons_per_loc * permit_locations
    labor_yen = nz(masters.get('labor_yen_per_person_year'))
    labor_cost = excel_round(persons * labor_yen, 0)
    tr.add(key='D', title='労務費', formula='D = ROUND((所要人数/地点 × 許可地点数) × 1人当たり労務費, 0)',
           inputs={'所要人数/地点': persons_per_loc, '許可地点数': permit_locations, '1人当たり労務費(円/人年)': labor_yen}, value=labor_cost, unit='円')

    # Assets aggregates
    assets = entry.assets.copy()
    for col in ['投資額①','投資額②','償却率','修繕費率']:
        if col not in assets.columns:
            assets[col] = 0
    for col in ['投資額①','投資額②','償却率','修繕費率']:
        assets[col] = assets[col].apply(nz)

    B2 = float(assets['投資額①'].sum())
    B3 = float(assets['投資額②'].sum())
    B7 = B2 + B3

    tr.add(key='B②', title='投資額①計', formula='B② = Σ(償却資産 投資額①)', inputs={'rows': len(assets)}, value=excel_round(B2,0), unit='円')
    tr.add(key='B③', title='投資額②計', formula='B③ = Σ(償却資産 投資額②)', inputs={'rows': len(assets)}, value=excel_round(B3,0), unit='円')
    tr.add(key='B⑦', title='償却資産計', formula='B⑦ = B② + B③', inputs={'B②': B2, 'B③': B3}, value=excel_round(B7,0), unit='円')

    # E: repair
    default_repair_rate = nz(masters.get('repair_rate'))
    if assets['修繕費率'].sum() > 0:
        repair_cost = excel_round(float(((assets['投資額①']+assets['投資額②']) * assets['修繕費率']).sum()),0)
        note = '明細行の修繕費率'
    else:
        repair_cost = excel_round(B7 * default_repair_rate, 0)
        note = 'マスタ修繕費率'
    tr.add(key='E', title='修繕費', formula='E = ROUND(Σ(投資額×修繕費率),0) または ROUND(B⑦×修繕費率,0)',
           inputs={'B⑦': B7, '修繕費率': default_repair_rate}, value=repair_cost, unit='円', notes=note)

    # I: depreciation
    depreciation = excel_round(float(((assets['投資額①']+assets['投資額②']) * assets['償却率']).sum()), 0)
    tr.add(key='I', title='減価償却費', formula='I = ROUND(Σ(投資額×償却率),0)', inputs={'rows': len(assets)}, value=depreciation, unit='円')

    # Land: investment and evaluated within required area
    land = entry.land.copy()
    for col in ['取得面積(m2)','取得価格(円)','評価額(円)','所要面積(m2)']:
        if col not in land.columns:
            land[col] = 0
    for col in ['取得面積(m2)','取得価格(円)','評価額(円)','所要面積(m2)']:
        land[col] = land[col].apply(nz)

    import numpy as np
    area = land['取得面積(m2)'].replace({0: np.nan})
    land_unit_price = (land['取得価格(円)'] / area).fillna(0)
    land_unit_eval = (land['評価額(円)'] / area).fillna(0)

    land_invest = excel_round(float((land_unit_price * land['所要面積(m2)']).sum()), 0)
    land_eval_required = excel_round(float((land_unit_eval * land['所要面積(m2)']).sum()), 0)

    tr.add(key='土地投資額', title='土地投資額', formula='土地投資額 = Σ((取得価格/取得面積)×所要面積)', inputs={'rows': len(land)}, value=land_invest, unit='円')
    tr.add(key='f1', title='土地課税標準（所要面積分）', formula='f1 = Σ((評価額/取得面積)×所要面積)', inputs={'rows': len(land)}, value=land_eval_required, unit='円')

    # F: property tax
    land_tax_rate = nz(masters.get('land_tax_rate'))
    asset_tax_rate = nz(masters.get('asset_tax_rate'))
    reduction = nz(masters.get('reduction_factor'))

    land_tax = excel_round(land_eval_required * land_tax_rate, 0)
    asset_tax_base = (B2 * 0.5) + (B3 * reduction * 0.5)
    asset_tax = excel_round(asset_tax_base * asset_tax_rate, 0)
    property_tax = excel_round(land_tax + asset_tax, 0)

    tr.add(key='F', title='固定資産税',
           formula='F = ROUND(f1×土地税率,0) + ROUND(((B②/2)+(B③×軽減係数/2))×資産税率,0)',
           inputs={'f1': land_eval_required, '土地税率': land_tax_rate, 'B②': B2, 'B③': B3, '軽減係数': reduction, '資産税率': asset_tax_rate},
           value=property_tax, unit='円', notes=f'内訳: 土地={land_tax:.0f}, 建物等={asset_tax:.0f}')

    # H: road occupancy
    road = entry.road.copy()
    for col in ['共同住宅_地点数','共同住宅_単価','単独住宅_地点数','単独住宅_単価']:
        if col not in road.columns:
            road[col] = 0
    for col in ['共同住宅_地点数','共同住宅_単価','単独住宅_地点数','単独住宅_単価']:
        road[col] = road[col].apply(nz)
    road_occupancy = excel_round(float((road['共同住宅_地点数']*road['共同住宅_単価'] + road['単独住宅_地点数']*road['単独住宅_単価']).sum()), 0)
    tr.add(key='H', title='道路占用料', formula='H = Σ(共同地点数×単価 + 単独地点数×単価)', inputs={'rows': len(road)}, value=road_occupancy, unit='円')

    # J: other expenses
    expense_rate = nz(masters.get('expense_rate'))
    base_for_other = raw_cost + labor_cost + repair_cost + property_tax + road_occupancy + depreciation
    other_expenses = excel_round(base_for_other * expense_rate, 0)
    tr.add(key='J', title='その他経費', formula='J = ROUND((C+D+E+F+H+I)×諸経費率,0)', inputs={'基礎合計': base_for_other, '諸経費率': expense_rate}, value=other_expenses, unit='円')

    subtotal = excel_round(raw_cost + labor_cost + repair_cost + property_tax + road_occupancy + depreciation + other_expenses, 0)

    # L: remuneration
    rem_rate = nz(masters.get('remuneration_rate'))
    remuneration = excel_round((land_invest + B7) * rem_rate, 0)
    tr.add(key='L', title='事業報酬額', formula='L = ROUND((土地投資額 + B⑦)×標準報酬率,0)', inputs={'土地投資額': land_invest, 'B⑦': B7, '標準報酬率': rem_rate}, value=remuneration, unit='円')

    # K: corporate taxes
    self_cap = nz(masters.get('self_capital_ratio'))
    corp_coeff = nz(masters.get('corp_tax_coeff'))
    local_rate = nz(masters.get('local_corp_tax_rate'))
    inhabitant_rate = nz(masters.get('inhabitant_tax_rate'))

    corp_tax = excel_round(remuneration * self_cap * corp_coeff, 0)
    local_corp = excel_round(corp_tax * local_rate, 0)
    inhabitant = excel_round(corp_tax * inhabitant_rate, 0)

    corp_taxes = excel_round(corp_tax + local_corp + inhabitant, 0)

    tr.add(key='K', title='法人税等',
           formula='K = ROUND(L×自己資本比率×法人税係数,0) + ROUND(法人税×地方法人税率,0) + ROUND(法人税×住民税率,0)',
           inputs={'L': remuneration, '自己資本比率': self_cap, '法人税係数': corp_coeff, '地方法人税率': local_rate, '住民税率': inhabitant_rate},
           value=corp_taxes, unit='円', notes=f'内訳: 法人税={corp_tax:.0f}, 地方法人税={local_corp:.0f}, 住民税={inhabitant:.0f}')

    # G: business tax
    biz_rate = nz(masters.get('business_tax_rate'))
    biz_base = remuneration * self_cap
    business_tax = excel_round(biz_base * biz_rate / (1 - biz_rate), 0) if biz_rate < 1 else 0.0
    tr.add(key='G', title='事業税', formula='G = ROUND((L×自己資本比率)×事業税率/(1-事業税率),0)', inputs={'L': remuneration, '自己資本比率': self_cap, '事業税率': biz_rate}, value=business_tax, unit='円')

    total_cost = excel_round(subtotal + remuneration + corp_taxes + business_tax, 0)
    unit_cost = excel_round(total_cost / sales_m3, 2) if sales_m3 else 0.0

    lines = [
        ('原料費', raw_cost),
        ('労務費', labor_cost),
        ('修繕費', repair_cost),
        ('固定資産税', property_tax),
        ('事業税', business_tax),
        ('道路占用料', road_occupancy),
        ('減価償却費', depreciation),
        ('その他経費', other_expenses),
        ('小計', subtotal),
        ('事業報酬額', remuneration),
        ('法人税', corp_tax),
        ('地方法人税', local_corp),
        ('住民税', inhabitant),
        ('合計（総原価）', total_cost),
    ]
    df = pd.DataFrame(lines, columns=['項目','金額(円)'])
    df['構成比(%)'] = df['金額(円)'] / total_cost * 100 if total_cost else 0.0

    computed = {
        'raw_cost': raw_cost,
        'labor_cost': labor_cost,
        'repair_cost': repair_cost,
        'property_tax': property_tax,
        'business_tax': business_tax,
        'road_occupancy': road_occupancy,
        'depreciation': depreciation,
        'other_expenses': other_expenses,
        'subtotal': subtotal,
        'remuneration': remuneration,
        'corp_tax': corp_tax,
        'local_corp_tax': local_corp,
        'inhabitant_tax': inhabitant,
        'total_cost': total_cost,
        'sales_m3': sales_m3,
        'unit_yen_per_m3': unit_cost,
    }

    return Form2Table1(rows=df, sales_m3=sales_m3, unit_cost=unit_cost), tr, computed
