import streamlit as st
import pandas as pd
import numpy as np
import math
import json
from datetime import datetime

# =================================================================
# 1. 基幹演算ユーティリティ（端数処理・バリデーション）
# =================================================================
def floor_val(val, decimals=0):
    """指定桁数での切り捨て"""
    if val is None: return 0.0
    factor = 10 ** decimals
    return math.floor(val * factor) / factor

# =================================================================
# 2. マスターデータ（標準係数シートの構造化）
# =================================================================
# ※ 本来はCSVからロードするが、プロトタイプとして君の指定番地数値を定義
LAND_REQUIRED_AREAS = {"11": 295.0, "12": 350.0} # 標準係数B O4:X20
PREF_COEFFS = {1: {"name": "北海道", "std_sales": 8.8, "labor_unit": 5683000, "gas_ratio": 0.476}} # 標準係数B B4:G50

# =================================================================
# 3. アプリケーション・ステート初期化
# =================================================================
if 'db' not in st.session_state:
    st.session_state.db = {
        "pref_id": 1, "customers": 487.0,
        "asset_mode": "実績", "use_reduction": True,
        "labor_mode": "標準", "repair_mode": "標準",
        "demand_mode": "手入力",
        "actual_land_area": 649.1, "actual_land_price": 15300000.0,
        "land_id": "11",
        "assets_list": [
            {"name": "建物", "actual": 5368245.0, "std": 5000000.0, "is_reduction": True},
            {"name": "本支管", "actual": 36814400.0, "std": 35000000.0, "is_reduction": False}
        ],
        "tier_data": [
            {"群名": "A", "比率": 0.850},
            {"群名": "B", "比率": 0.130},
            {"群名": "C", "比率": 0.020}
        ]
    }

db = st.session_state.db

# =================================================================
# 4. 計算エンジン：ナガセ・プロトコル
# =================================================================
def run_calculation():
    # --- A. 販売量算定 ---
    pref = PREF_COEFFS[db["pref_id"]]
    db["res_sales_a1"] = pref["std_sales"]
    db["res_vol_A"] = floor_val(db["res_sales_a1"] * db["customers"] * 12, 3)

    # --- B. 土地の認容面積判定（自動カット） ---
    req_area = LAND_REQUIRED_AREAS.get(db["land_id"], 0.0)
    db["res_land_area_final"] = min(db["actual_land_area"], req_area)
    # 単価計算（実績ベース）
    unit_price = db["actual_land_price"] / db["actual_land_area"]
    db["res_land_invest"] = db["res_land_area_final"] * unit_price

    # --- C. 投資額の振り分け（投資額①・②） ---
    db["invest_1"] = db["res_land_invest"] # 土地は通常①
    db["invest_2"] = 0.0
    for asset in db["assets_list"]:
        val = asset["actual"] if db["asset_mode"] == "実績" else asset["std"]
        if asset["is_reduction"] and db["use_reduction"]:
            db["invest_2"] += val
        else:
            db["invest_1"] += val

    # --- D. 労務費・原料費 ---
    staff = floor_val(db["customers"] * 0.0031, 4)
    db["res_labor_cost"] = math.floor(staff * pref["labor_unit"])
    db["res_raw_cost"] = math.floor((db["res_vol_A"] / pref["gas_ratio"]) * 106.05)

    # --- E. 修繕費 ---
    if db["repair_mode"] == "実績":
        db["res_repair"] = 1571432.0
    else:
        db["res_repair"] = math.floor((db["invest_1"] + db["invest_2"]) * 0.03)

    # 総計
    db["total_cost"] = db["res_raw_cost"] + db["res_labor_cost"] + db["res_repair"] + 5000000.0 # その他固定

# =================================================================
# 5. メインUIレイアウト
# =================================================================
st.title("🧪 Gas Lab Engine v2.5")

# サイドバー：経営判断スイッチ
with st.sidebar:
    st.header("🕹️ Strategic Switches")
    db["asset_mode"] = st.radio("投資額ソース", ["実績", "標準"], index=0)
    db["use_reduction"] = st.checkbox("減免措置を適用", value=db["use_reduction"])
    db["repair_mode"] = st.radio("修繕費ソース", ["実績", "標準"], index=1)
    db["demand_mode"] = st.radio("需要構成率ソース", ["手入力", "都道府県引用"], index=0)
    
    if st.button("🚀 計算実行"):
        run_calculation()
        st.success("計算完了")

# タブ構成
t_dash, t_asset, t_rate = st.tabs(["🚀 Dashboard", "🏗️ 資産・土地認容性", "📊 レートメイク"])

with t_dash:
    st.header("算定総括原価（速報値）")
    c1, c2 = st.columns(2)
    c1.metric("総括原価", f"¥{db.get('total_cost', 0):,.0f}")
    c1.metric("投資額①", f"¥{db.get('invest_1', 0):,.0f}")
    c2.metric("投資額②（減免対象）", f"¥{db.get('invest_2', 0):,.0f}")
    
    st.divider()
    st.subheader("原価の内訳")
    cost_data = {
        "項目": ["原料費", "労務費", "修繕費"],
        "金額": [db.get("res_raw_cost", 0), db.get("res_labor_cost", 0), db.get("res_repair", 0)]
    }
    st.bar_chart(pd.DataFrame(cost_data).set_index("項目"))

with t_asset:
    st.header("土地の認容面積判定")
    col_l, col_r = st.columns(2)
    with col_l:
        st.write("### 実績値")
        st.write(f"実績面積: {db['actual_land_area']} m2")
        st.write(f"実績総額: ¥{db['actual_land_price']:,.0f}")
    with col_r:
        st.write("### 判定結果（自動カット適用）")
        st.info(f"標準所要面積上限: {LAND_REQUIRED_AREAS[db['land_id']]} m2")
        st.metric("認容面積", f"{db.get('res_land_area_final', 0)} m2")
        st.metric("認容投資額", f"¥{db.get('res_land_invest', 0):,.0f}")

with t_rate:
    st.header("需要家群の動的設定")
    if db["demand_mode"] == "手入力":
        # 動的グリッド
        df_tier = pd.DataFrame(db["tier_data"])
        edited_df = st.data_editor(df_tier, num_rows="dynamic", use_container_width=True)
        
        total = edited_df["比率"].sum()
        st.progress(min(total, 1.0), text=f"合計: {total:.4f}")
        
        if abs(total - 1.0) < 0.0001:
            st.success("✅ 合計が1.0に一致しました")
            db["tier_data"] = edited_df.to_dict('records')
        else:
            st.error("❌ 合計を1.0に調整してください")
    else:
        st.info("都道府県データを引用しています（3段階固定）")
