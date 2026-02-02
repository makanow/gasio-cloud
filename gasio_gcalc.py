import streamlit as st
import pandas as pd
import numpy as np
import json
from datetime import datetime
import plotly.graph_objects as go

# =================================================================
# 1. ページ構成とテーマ
# =================================================================
st.set_page_config(page_title="Gas Lab - Strategic Engine v1.1", layout="wide")

# =================================================================
# 2. 堅牢なセッション状態の初期化 (KeyError対策)
# =================================================================
# dbが存在しない、もしくは構造が古い場合に備え、毎回構造を確認する関数
def initialize_db():
    default_db = {
        "meta": {"client": "滝川ガス株式会社", "date": str(datetime.now().date())},
        "basic": {"pref": "北海道", "customer_count": 487, "tax_rate": 0.22},
        "input_sales": {
            "a1_monthly_avg": 8.833, 
            "raw_material_unit_price": 106.05
        },
        "input_assets": {
            "land_invest": 6953445,
            "building_invest": 5368245,
            "depreciation_rate": 0.03
        },
        "ratemake": {
            "base_fees": {"A": 1200, "B": 1800, "C": 4050},
            "unit_prices": {"A": 550, "B": 475, "C": 400},
            "new_base_a": 1200, # 直接参照用のキーを明示的に配置
            "new_unit_a": 550,
            "current_revenue": 27251333
        }
    }
    
    if 'db' not in st.session_state:
        st.session_state.db = default_db
    else:
        # 構造が変わっている場合に備え、欠落しているキーを補完する
        for key, value in default_db.items():
            if key not in st.session_state.db:
                st.session_state.db[key] = value
            elif isinstance(value, dict):
                for k, v in value.items():
                    if k not in st.session_state.db[key]:
                        st.session_state.db[key][k] = v

initialize_db()

# =================================================================
# 3. 計算エンジン (ロジックの心臓部)
# =================================================================
def calculate_all():
    db = st.session_state.db
    # 産気率などのマスター値（本来はCSVから）
    pref_master = {"北海道": 0.476, "その他": 0.460}
    gas_ratio = pref_master.get(db["basic"]["pref"], 0.460)
    
    # --- 販売量 ---
    db["calc_sales_volume"] = db["input_sales"]["a1_monthly_avg"] * db["basic"]["customer_count"] * 12
    
    # --- 原価 ---
    db["calc_raw_material"] = (db["calc_sales_volume"] / gas_ratio) * db["input_sales"]["raw_material_unit_price"]
    db["calc_labor"] = db["basic"]["customer_count"] * 0.0031 * 5683000
    db["calc_depreciation"] = db["input_assets"]["building_invest"] * db["input_assets"]["depreciation_rate"]
    db["calc_total_cost"] = db["calc_raw_material"] + db["calc_labor"] + db["calc_depreciation"] + 1571432
    
    # --- 収支 ---
    # 新料金でのシミュレーション（簡易版）
    db["calc_new_revenue"] = (db["ratemake"]["new_base_a"] * db["basic"]["customer_count"] * 12) + (db["ratemake"]["new_unit_a"] * db["calc_sales_volume"])
    db["calc_gap"] = db["calc_new_revenue"] - db["calc_total_cost"]

calculate_all()

# =================================================================
# 4. メインUI
# =================================================================
st.sidebar.title("🧪 Gas Lab Engine")
app_mode = st.sidebar.selectbox("モード", ["実務・認可申請", "経営シミュレーション"])

# ファイル書き出し・読み込み
with st.sidebar:
    st.divider()
    if st.button("セッションを完全にリセット"):
        st.session_state.clear()
        st.rerun()
    
    json_data = json.dumps(st.session_state.db, indent=4, ensure_ascii=False)
    st.download_button("設定ファイルを書き出す", json_data, file_name="gas_lab_data.json")

# タブ構成
tabs = st.tabs(["🚀 Dash", "📋 基礎", "💰 原価", "📊 料金", "📄 申請"])

with tabs[0]: # Dashboard
    st.header(f"Project: {st.session_state.db['meta']['client']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("総原価", f"¥{st.session_state.db['calc_total_cost']:,.0f}")
    c2.metric("収支過不足", f"¥{st.session_state.db['calc_gap']:,.0f}", delta=f"{st.session_state.db['calc_gap']:,.0f}")
    c3.metric("販売量", f"{st.session_state.db['calc_sales_volume']:,.0f} ㎥")

with tabs[1]: # 基礎データ入力
    st.session_state.db["input_sales"]["a1_monthly_avg"] = st.number_input(
        "月平均販売量 (a1)", value=st.session_state.db["input_sales"]["a1_monthly_avg"], format="%.3f"
    )
    st.session_state.db["basic"]["customer_count"] = st.number_input(
        "地点数 (a2)", value=st.session_state.db["basic"]["customer_count"]
    )

with tabs[3]: # レートメイク (エラーの起きた場所)
    st.header("レートメイク・シミュレーター")
    col_ctrl, col_graph = st.columns([1, 2])
    
    with col_ctrl:
        # ここでKeyErrorが起きないよう、initialize_dbで構造を保証している
        st.session_state.db["ratemake"]["new_base_a"] = st.slider(
            "A群 基本料金", 500, 2000, int(st.session_state.db["ratemake"]["new_base_a"])
        )
        st.session_state.db["ratemake"]["new_unit_a"] = st.slider(
            "A群 単位料金", 300, 800, int(st.session_state.db["ratemake"]["new_unit_a"])
        )
        calculate_all()
        st.success(f"想定収益: ¥{st.session_state.db['calc_new_revenue']:,.0f}")

    with col_graph:
        fig = go.Figure(go.Bar(
            x=['総原価', '想定収益'], 
            y=[st.session_state.db['calc_total_cost'], st.session_state.db['calc_new_revenue']],
            marker_color=['#e74c3c', '#3498db']
        ))
        st.plotly_chart(fig, use_container_width=True)

with tabs[4]: # 申請書
    st.button("様式第1 第1表 (Excel形式) でエクスポート")
