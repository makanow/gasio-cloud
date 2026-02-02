import streamlit as st
import pandas as pd
import math

# =================================================================
# 1. 初期化ロジック (NameError 対策)
# =================================================================
def initialize_state():
    # セッション内に db がない場合のみデフォルト値をセット
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
            # 計算結果の受け皿も初期化しておく
            "res_land_invest": 0.0,
            "res_land_area": 0.0,
            "res_land_eval": 0.0,
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

# 最初に初期化を実行
initialize_state()
db = st.session_state.db  # これでこれ以降、どこでも db が使える

# =================================================================
# 2. 精密計算エンジン (関数内に集約)
# =================================================================
def run_full_engine():
    # --- A. 土地：ROUND(単価, 0) * 面積 ---
    req_area = 295.0 # 標準係数B O4:X20 (3t未満)
    db["res_land_area"] = min(db["actual_land_area"], req_area)
    
    # 単価を0桁で丸める
    unit_price = round(db["actual_land_price"] / db["actual_land_area"], 0)
    db["res_land_invest"] = unit_price * db["res_land_area"]
    
    # 評価額も同様
    unit_eval = round(db["actual_land_eval"] / db["actual_land_area"], 0)
    db["res_land_eval"] = unit_eval * db["res_land_area"]

    # --- B. 投資額の振り分け (①・②) ---
    db["invest_1"] = db["res_land_invest"]
    db["invest_2"] = 0.0
    for asset in db["assets_list"]:
        val = asset["actual"] if db["asset_mode"] == "実績" else asset["std"]
        if asset["is_reduction"] and db["use_reduction"]:
            db["invest_2"] += val
        else:
            db["invest_1"] += val

    # --- C. 租税公課 (1/2 減免) ---
    tax_base_assets = db["invest_1"] + (db["invest_2"] * 0.5)
    db["tax_assets"] = math.floor(tax_base_assets * 0.014)
    db["tax_land"] = math.floor(db["res_land_eval"] * 0.014)
    db["res_tax_total"] = db["tax_assets"] + db["tax_land"]

# =================================================================
# 3. メイン UI
# =================================================================
st.title("🧪 Gas Lab Engine : Precision Logic")

with st.sidebar:
    st.header("⚙️ 設定スイッチ")
    # 代入ではなく、値の取得と更新を同時に行う
    db["asset_mode"] = st.radio("投資額ソース", ["実績", "標準"], index=0)
    db["use_reduction"] = st.checkbox("減免措置を適用", value=db["use_reduction"])
    
    if st.button("🚀 計算実行"):
        run_full_engine()
        st.success("計算完了")

# 結果表示 (Dashboard)
c1, c2, c3 = st.columns(3)
c1.metric("認容土地投資額", f"¥{db['res_land_invest']:,.0f}")
c2.metric("租税公課 合計", f"¥{db.get('res_tax_total', 0):,.0f}")
c3.metric("投資額② (減免対象)", f"¥{db['invest_2']:,.0f}")

st.divider()
with st.expander("🛠️ 土地計算のディテール"):
    st.write(f"実績単価: ¥{round(db['actual_land_price']/db['actual_land_area'], 2):,}")
    st.write(f"丸め後単価: ¥{round(db['actual_land_price']/db['actual_land_area'], 0):,}")
    st.write(f"認容面積上限: {295.0} m2")
