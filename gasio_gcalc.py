import streamlit as st
import pandas as pd
import math

# =================================================================
# 1. 車両スライド計算定数（標準係数A T3:AA24 相当）
# =================================================================
# 本来はHKコードに応じた行選択だが、プロトタイプとして特定行の単価をセット
VEHICLE_TIER_MASTER = {
    "HK10": { # 例: 平成19年5月7日以降取得
        "tiers": [250, 1000, 2000, 3000, 4000, 5000, 10000, 99999],
        "prices": [4440, 2610, 1940, 1610, 1410, 1270, 1010, 800] # CA1-CA8
    }
}

# =================================================================
# 2. 車両積算エンジン
# =================================================================
def calc_vehicle_investment(customers, hk_code="HK10"):
    master = VEHICLE_TIER_MASTER[hk_code]
    total_invest = 0
    remaining = customers
    prev_limit = 0
    
    for limit, price in zip(master["tiers"], master["prices"]):
        if remaining <= 0: break
        
        # この階層に収まる地点数を算出
        count_in_tier = min(remaining, limit - prev_limit)
        total_invest += count_in_tier * price
        
        remaining -= count_in_tier
        prev_limit = limit
        
    return total_invest

# =================================================================
# 3. 土地・車両を統合したメイン計算
# =================================================================
def run_final_logic():
    db = st.session_state.db
    
    # --- A. 土地：ナガセ指定 ROUND(単価, 0) * 面積 ---
    req_area = 295.0 # 標準係数B O4:X20 (3t未満)
    db["res_land_area"] = min(db["actual_land_area"], req_area)
    
    # 単価を0桁で丸める (Excel: ROUND(価格/面積, 0))
    unit_price = round(db["actual_land_price"] / db["actual_land_area"], 0)
    db["res_land_invest"] = unit_price * db["res_land_area"]
    
    # 土地評価額も同様
    unit_eval = round(db["actual_land_eval"] / db["actual_land_area"], 0)
    db["res_land_eval"] = unit_eval * db["res_land_area"]

    # --- B. 車両：スライド積算 ---
    # 車両シートC4の取得時期判定は将来的にHKコード検索へ
    db["res_vehicle_invest"] = calc_vehicle_investment(db["customers"], "HK10")

# =================================================================
# 4. UIセクション
# =================================================================
st.title("🧪 Gas Lab Engine v2.6 : Precision Edition")

with st.sidebar:
    st.header("📋 基本入力")
    db = st.session_state.db
    db["customers"] = st.number_input("供給地点数", value=float(db["customers"]))
    db["actual_land_area"] = st.number_input("土地実績面積", value=649.1)
    db["actual_land_price"] = st.number_input("土地実績価格", value=15300000.0)
    db["actual_land_eval"] = st.number_input("土地実績評価額", value=6126190.0)

if st.button("🚀 計算実行（精密検証）"):
    run_final_logic()
    st.success("計算完了：端数処理およびスライド積算を適用しました")

# 結果表示
c1, c2, c3 = st.columns(3)
with c1:
    st.subheader("土地認容投資額")
    st.metric("認容投資額", f"¥{db.get('res_land_invest', 0):,.0f}")
    st.caption("※ROUND(単価, 0) * 認容面積")
with c2:
    st.subheader("車両標準投資額")
    st.metric("積算投資額", f"¥{db.get('res_vehicle_invest', 0):,.0f}")
    st.caption("※地点数別スライド積算適用")
with c3:
    st.subheader("土地認容評価額")
    st.metric("認容評価額", f"¥{db.get('res_land_eval', 0):,.0f}")
