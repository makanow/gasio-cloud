import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
from datetime import datetime

# =================================================================
# 1. 究極の初期化ロジック (エラーの根絶とデータの厚み)
# =================================================================
def initialize_grand_engine():
    if 'db' not in st.session_state:
        st.session_state.db = {
            "basic": {"pref": "北海道", "customers": 487, "labor_unit": 5683000.0},
            "sales": {
                "a1": 8.833, # 1地点平均
                "monthly_data": [4620, 4525, 4325, 3725, 3525, 3425, 3425, 3425, 3525, 3825, 4325, 5934], # 1_aシート実績
                "buy_price": 106.05
            },
            "ratemake": {
                "A": {"base": 1200.0, "unit": 550.0, "ratio": 0.85}, # 全てfloatで統一
                "B": {"base": 1800.0, "unit": 475.0, "ratio": 0.13},
                "C": {"base": 4050.0, "unit": 400.0, "ratio": 0.02},
                "current_rev": 27251333.0
            },
            "coeffs": {"gas_ratio": 0.476, "labor_coeff": 0.0031}
        }

initialize_grand_engine()
db = st.session_state.db

# =================================================================
# 2. 計算コア（Excelの全細胞を同期）
# =================================================================
def refresh_calculations():
    # 販売量算定 (a1 * a2 * 12)
    db["res_vol"] = db["sales"]["a1"] * db["basic"]["customers"] * 12
    # 原価配分 (1_bシート)
    db["res_raw_cost"] = (db["res_vol"] / db["coeffs"]["gas_ratio"]) * db["sales"]["buy_price"]
    db["res_labor_cost"] = (db["basic"]["customers"] * db["coeffs"]["labor_coeff"]) * db["basic"]["labor_unit"]
    db["res_total_cost"] = db["res_raw_cost"] + db["res_labor_cost"] + 5000000.0 # 固定費等

refresh_calculations()

# =================================================================
# 3. 10倍リッチなUIコンポーネント
# =================================================================
st.title("🧪 Gas Lab Engine - Grand Research Lab")

tabs = st.tabs(["🚀 Dashboard", "📊 需要・販売量精査", "🏗️ 資産・原価構造", "📈 レートメイク戦略"])

# --- Tab 2: 需要・販売量 (ここを徹底的に描き込む) ---
with tabs[1]:
    st.header("様式第１ 第１表：需要および販売量の詳細分析")
    
    col_main, col_ev = st.columns([2, 1])
    
    with col_main:
        # 12ヶ月の需要カーブを可視化
        months = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(x=months, y=db["sales"]["monthly_data"], mode='lines+markers', name='月別実績', line=dict(color='#1f77b4', width=4)))
        fig_vol.update_layout(title="算定期間における需要変動（季節性指標）", template="plotly_white")
        st.plotly_chart(fig_vol, use_container_width=True)

        # 詳細入力
        c1, c2 = st.columns(2)
        db["sales"]["a1"] = c1.number_input("月平均販売量 (a1)", value=float(db["sales"]["a1"]), format="%.3f", step=0.001)
        db["basic"]["customers"] = c2.number_input("供給地点数 (a2)", value=int(db["basic"]["customers"]), step=1)
        
    with col_ev:
        st.markdown(f"""
        <div style="background:#f0f2f6; padding:20px; border-radius:10px; border-left: 5px solid #1f77b4;">
        <strong>🔍 エビデンス・ロジック</strong><br>
        <small>参照: G-Calc_master.xlsx [販売量]シート</small><br><br>
        年間販売量(A) = <span style="color:#d35400; font-weight:bold;">{db['res_vol']:,.2f} ㎥</span><br>
        ピーク月使用量: <strong>{max(db['sales']['monthly_data']):,.0f} ㎥</strong><br>
        産気率(北海道): <strong>{db['coeffs']['gas_ratio']}</strong>
        </div>
        """, unsafe_allow_html=True)
        st.info("💡 建築家の視点: 寒冷地特有の冬季ピークが顕著だ。この需要格差が導管設計の基礎となる。")

# --- Tab 4: レートメイク (エラーを修正した究極のシミュレータ) ---
with tabs[3]:
    st.header("戦略的レートメイク：収支シミュレーション")
    
    col_set, col_viz = st.columns([1, 1])
    
    with col_set:
        for g in ["A", "B", "C"]:
            st.subheader(f"【{g}群】の設定")
            # float()で包むことでMixedTypeを完全回避
            db["ratemake"][g]["base"] = st.number_input(f"{g}群 基本料金", value=float(db["ratemake"][g]["base"]), step=10.0)
            db["ratemake"][g]["unit"] = st.number_input(f"{g}群 単位料金", value=float(db["ratemake"][g]["unit"]), step=0.1)
        
        refresh_calculations()
        rev_rate = (db["res_total_cost"] / db["ratemake"]["current_rev"] - 1) * 100
        st.metric("必要改定率", f"{rev_rate:.2f}%", delta=f"{rev_rate-12.0:.2f}% vs 業界平均")

    with col_viz:
        # 収支バランスのゲージ
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = (db["res_total_cost"] / db["ratemake"]["current_rev"]) * 100,
            title = {'text': "原価回収率 (%)"},
            gauge = {'axis': {'range': [90, 110]},
                     'bar': {'color': "#2ecc71"},
                     'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 100}}))
        st.plotly_chart(fig_gauge, use_container_width=True)
