import streamlit as st
import pandas as pd
import math

# =================================================================
# 1. ページ設定とセッション初期化（ここが最優先）
# =================================================================
st.set_page_config(page_title="Gas Lab Engine v2.7", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = {
        "customers": 487.0,
        "pref_id": 1,
        "asset_mode": "実績",
        "use_reduction": True,
        "actual_land_price": 15300000.0,
        "actual_land_area": 649.1,
        "actual_land_eval": 6126190.0,
        "land_id": "11",
        "invest_1": 0.0,
        "invest_2": 0.0,
        "assets_list": [
            {"name": "建物", "actual": 5368245.0, "std": 5000000.0, "is_reduction": True},
            {"name": "本支管", "actual": 36814400.0, "std": 35000000.0, "is_reduction": False}
        ],
        "override_return_rate": False,
        "active_return_rate": 0.03,
        "actual_repair_total": 1571432.0,
        "repair_mode": "標準"
    }

# 参照を短縮
db = st.session_state.db

# =================================================================
# 2. 精密計算エンジン（ナガセ・プロトコル）
# =================================================================
def run_full_engine():
    # --- A. 土地認容 (ROUND & MIN) ---
    req_area = 295.0 # 標準係数B O4:X20 (3t未満)
    db["res_land_area"] = min(db["actual_land_area"], req_area)
    unit_price = round(db["actual_land_price"] / db["actual_land_area"], 0)
    db["res_land_invest"] = unit_price * db["res_land_area"]
    unit_eval = round(db["actual_land_eval"] / db["actual_land_area"], 0)
    db["res_land_eval"] = unit_eval * db["res_land_area"]

    # --- B. 投資額の振り分け ---
    db["invest_1"] = db["res_land_invest"]
    db["invest_2"] = 0.0
    for asset in db["assets_list"]:
        val = asset["actual"] if db["asset_mode"] == "実績" else asset["std"]
        if asset["is_reduction"] and db["use_reduction"]:
            db["invest_2"] += val
        else:
            db["invest_1"] += val

    # --- C. 減価償却費 (個別計算・端数累積) ---
    total_dep = 0.0
    for asset in db["assets_list"]:
        val = asset["actual"] if db["asset_mode"] == "実績" else asset["std"]
        total_dep += (val * 0.03) # 償却率は投資単位ごと
    db["res_depreciation_total"] = total_dep

    # --- D. 租税公課 (1/2減免ロジック) ---
    tax_base_assets = db["invest_1"] + (db["invest_2"] * 0.5)
    tax_assets = math.floor(tax_base_assets * 0.014)
    tax_land = math.floor(db["res_land_eval"] * 0.014)
    db["res_tax_total"] = tax_assets + tax_land

    # --- E. 事業報酬 ---
    asset_base = db["invest_1"] + db["invest_2"] + db["res_land_invest"]
    db["res_return_on_assets"] = math.floor(asset_base * db["active_return_rate"])

# =================================================================
# 3. UI セクション
# =================================================================
with st.sidebar:
    st.header("⚙️ 算定スイッチ")
    db["asset_mode"] = st.radio("投資額ソース", ["実績", "標準"], index=0)
    db["use_reduction"] = st.checkbox("減免措置を適用", value=db["use_reduction"])
    st.divider()
    db["override_return_rate"] = st.checkbox("事業報酬率を手入力する", value=db["override_return_rate"])
    if db["override_return_rate"]:
        db["active_return_rate"] = st.number_input("事業報酬率", value=0.03, step=0.001, format="%.3f")
    else:
        st.info("標準報酬率: 3.0% (標準係数B K8)")
    
    if st.button("🚀 計算実行"):
        run_full_engine()

# 結果表示
st.title("🧪 Gas Lab Engine : 財務ロジック検証")
c1, c2, c3 = st.columns(3)
c1.metric("総括原価（仮）", f"¥{db.get('res_depreciation_total',0) + db.get('res_tax_total',0) + db.get('res_return_on_assets',0):,.0f}")
c2.metric("租税公課", f"¥{db.get('res_tax_total',0):,.0f}")
c3.metric("事業報酬", f"¥{db.get('res_return_on_assets',0):,.0f}")

st.divider()
st.subheader("📋 減免措置の適用結果")
st.write(f"投資額① (通常): ¥{db['invest_1']:,.0f}")
st.write(f"投資額② (減免): ¥{db['invest_2']:,.0f}")
st.caption("※租税公課の計算では、投資額②を 50% に圧縮して課税標準額を算出しています。")
